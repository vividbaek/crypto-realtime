# spark_jobs/kafka_reader.py
"""
사실상 kafka의 함수 모음 집(데이터 읽고 불러오는 용도)
단독으로 실행할 때는 depth 토픽을 1초마다 콘솔에 찍는 테스트/확인용
stream_preprocess.py 같은 전처리 job이 여기서 create, read, parse등 import해서 사용
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, get_json_object

# 스파크 작업을 시작하기 위한 "환경 설정"
def create_spark_session(app_name="BinanceProcessor"):
    """
    Spark 세션 생성 (재사용 가능)
    appname은 토픽임
    spark.jars.pacages: 카프카 전용 라이브러리 불러옴
    checkpointLocation: 스트리밍 중 에러 났을 때, 기록하는 것
    log4j.properties: 필요한 로그만 보려고 정리함.
    """
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1") \
        .config("spark.sql.streaming.checkpointLocation", f"/tmp/checkpoint-{app_name}") \
        .config("spark.driver.extraJavaOptions", "-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties") \
        .config("spark.executor.extraJavaOptions", "-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties") \
        .getOrCreate()

def read_from_kafka(spark, topic, starting_offsets="latest"):
    """
    Kafka에서 데이터 읽기 (재사용 가능)
    kafka.bootstrap.servers: kafka29092라는 주소로 접속
    subscribe: 인자로 받은 topic 구독
    startingOffsets: latest는 지금부터, earlist는 과거 데이터부터 다 가져오겠다는 것
    failOnDataLoss: 데이터가 일부 없어도 멈추지 말고 계속 진행(안전장치)
    maxOffsetsPerTrigger: 한번에 너무 많이 가져오면 렉 걸리니 1,000개씩으로 제한
    """
    return spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", topic) \
        .option("startingOffsets", starting_offsets) \
        .option("kafka.session.timeout.ms", "60000") \
        .option("kafka.request.timeout.ms", "90000") \
        .option("kafka.max.poll.interval.ms", "300000") \
        .option("kafka.heartbeat.interval.ms", "10000") \
        .option("kafka.metadata.max.age.ms", "300000") \
        .option("kafka.reconnect.backoff.ms", "50") \
        .option("kafka.reconnect.backoff.max.ms", "1000") \
        .option("failOnDataLoss", "false") \
        .option("maxOffsetsPerTrigger", "1000") \
        .load()

###### 카프카에서 온 데이터는 value라는 컬럼 안에 모든 내용이 JSON 문자열로 있음 (파싱해야함) ####
def parse_depth_data(df):
    """
    Depth 데이터 파싱 (재사용 가능)
    바이낸스의 Depth 데이터에서 매수/매도 1호가 가격(bid_price, ask_price)만 가져옴
    $data,b[0][0] JSON 구조 안에서 위치를 찾아감감
    """
    return df.select(
        get_json_object(col("value").cast("string"), "$.symbol").alias("symbol"),
        get_json_object(col("value").cast("string"), "$.data.b[0][0]").cast("double").alias("bid_price"),
        get_json_object(col("value").cast("string"), "$.data.a[0][0]").cast("double").alias("ask_price"),
        col("timestamp").alias("kafka_timestamp")
    )


def parse_trade_data(df):
    """
    aggTrade 데이터 파싱 (재사용 가능). 체결가/수량/시각 추출.
    실시간 체결 내역(agggTrade)처리
    바이낸스에서는 시간을 밀리초(ms)로 줌. 윈도우 집계를 위해 1,000우로 나눠처 초로 변경
    .catst(string) 카프카는 데이터를 효율적으로 보관하기 위해 이진수 형태로 저장(binary -> string으로 변경)
    alias는 별칭
    """
    v = col("value").cast("string")
    return df.select(
        get_json_object(v, "$.symbol").alias("symbol"),
        (get_json_object(v, "$.data.p").cast("double")).alias("price"),
        (get_json_object(v, "$.data.q").cast("double")).alias("quantity"),
        (get_json_object(v, "$.data.T").cast("long") / 1000).alias("event_time_sec"),  # 초 단위로 윈도우용
        get_json_object(v, "$.data.m").cast("boolean").alias("is_buyer_maker"),
    )


def parse_kline_data(df):
    """Kline(1분봉) 데이터 파싱. Binance가 이미 1분 집계한 값."""
    v = col("value").cast("string")
    return df.select(
        get_json_object(v, "$.symbol").alias("symbol"),
        (get_json_object(v, "$.data.k.t").cast("long") / 1000).alias("window_start_sec"),
        get_json_object(v, "$.data.k.o").cast("double").alias("open"),
        get_json_object(v, "$.data.k.h").cast("double").alias("high"),
        get_json_object(v, "$.data.k.l").cast("double").alias("low"),
        get_json_object(v, "$.data.k.c").cast("double").alias("close"),
        get_json_object(v, "$.data.k.v").cast("double").alias("volume"),
        get_json_object(v, "$.data.k.n").cast("long").alias("trades"),
        get_json_object(v, "$.data.k.x").cast("boolean").alias("is_candle_closed"),
    )

def main():
    import time
    
    spark = create_spark_session("BinanceDepthReader")
    
    # Kafka는 이미 실행 중. Consumer 연결 전 짧은 대기 (coordinator 대비)
    print("⏳ Kafka 연결 전 대기 (5초)...")
    time.sleep(5)
    
    # Kafka 읽기 (earliest로 변경하여 기존 데이터도 읽기)
    print("📥 Kafka에서 데이터 읽기 시작...")
    kafka_df = read_from_kafka(spark, "binance-depth", starting_offsets="earliest")
    
    # 파싱
    parsed_df = parse_depth_data(kafka_df)
    
    # 출력 (1초마다 배치 처리)
    print("🚀 스트리밍 쿼리 시작... (1초마다 배치 처리)")
    query = parsed_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .trigger(processingTime='1 second') \
        .start()
    
    query.awaitTermination()

if __name__ == "__main__":
    main()