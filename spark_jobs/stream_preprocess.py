"""
Kafka 스트림 전처리: aggTrade → 1분봉(OHLCV) 집계 후 콘솔 출력.

- binance-trade(aggTrade)를 읽어서 1분 tumbling window로 집계
- open=first(price), high=max, low=min, close=last, volume=sum(qty), count=체결건수
- 이후 ClickHouse 적재는 foreachBatch로 확장 가능

실행: 스파크 마스터 컨테이너에서
  spark-submit --master spark://spark-master:7077 --packages ... stream_preprocess.py
또는 ./scripts/start-spark-job.sh 에서 이 파일로 변경
"""
import time
from pyspark.sql import SparkSession
# 데이터 처리에 필요한 도구들 (특히 window는 시간 쪼개는 도구)
from pyspark.sql.functions import (
    col, first, last, min as spark_min, max as spark_max, sum as spark_sum, count,
    window, from_unixtime,
)
# kafka_reader에서 만든 데이터 불러옴
from kafka_reader import create_spark_session, read_from_kafka, parse_trade_data


def agg_trade_to_1m_ohlcv(parsed_trade_df):
    """
    aggTrade 파싱 결과를 1분 tumbling window로 집계 → OHLCV.
    event_time_sec 기준으로 1분 구간 묶음.
    with_ts내에서 col("event_time_sec")는 바이낸ㅅ에서 처음 온 데이터
    from_unixtime(): 사람이 읽을 수 있는 문자열로 바꿈 + spark가 계산하기 위해 timestap로 변경. 
    또한 unixtime이 초단위라고 확실하게 알려줌(밀리초단위 / 초단위 잘 구분해줌)
    "event_ts"는 변환된 시간 객체가 담길 새로운 컬럼 이름
    with_ts: event_ts 컬럼이 추가된 새로운 데이터 프레임
    with_window 내부: Tumbling Window 기법.event_ts를 기준으로 0~59초까지를 하나의 상자로 묶음
    agg(...): 뭉쳐진 데이터들을 대상으로 수학적 계산 진행
    selectL 계산은 끝났지만 window 컬럼이 구조체 형태({start, end}) 형태라서 직렬화 함.
    """
    # 초 단위 → timestamp (윈도우 함수용)
    with_ts = parsed_trade_df.withColumn(
        "event_ts",
        from_unixtime(col("event_time_sec")).cast("timestamp")
    )
    with_window = with_ts.withColumn("window", window(col("event_ts"), "1 minute"))

    return with_window.groupBy("window", "symbol").agg(
        first("price").alias("open"),
        spark_max("price").alias("high"),
        spark_min("price").alias("low"),
        last("price").alias("close"),
        spark_sum("quantity").alias("volume"),
        count("*").alias("trades_count"),
    ).select(
        col("window.start").alias("window_start"),
        col("symbol"),
        col("open"), col("high"), col("low"), col("close"),
        col("volume"), col("trades_count"),
    )


def main():
    spark = create_spark_session("StreamPreprocess-1mOHLCV")

    # Kafka는 이미 start.sh로 실행 중. Consumer 연결 전 짧은 대기만 (재시작 직후 coordinator 대비)
    print("⏳ Kafka 연결 전 대기 (5초)...")
    time.sleep(5)

    print("📥 binance-trade 구독 중...")
    kafka_df = read_from_kafka(spark, "binance-trade", starting_offsets="latest")

    parsed = parse_trade_data(kafka_df)
    ohlcv_1m = agg_trade_to_1m_ohlcv(parsed)

    print("🚀 1분봉 집계 스트리밍 시작 (1분마다 트리거)...")
    """
    writeStream: 지금까지 작성한 코드(readStreanm agg)는 실제로는 아무 일도 하지 않고 게획만 세운 상태
    writestream을 만나는 순가 spark는 시작함.
    .outputMode: 스트리밍 데이터 출력 여러 방식 있지만, 1분봉에는 update 모드 효율적
    update 몯: 1분이 지날 때마다 새롭게 계싼된 1분봉 결과값만 딱 찍어줌 (바뀐 데이터만 보여줌)
    format(console) 결과물 DB에 저장하지 않고 일단 터미널 콘솔 출력
    option("truncate", False): 데이터 길면 ...으로 생략하는데, 생략하지말고 전체 다
    .option(checkpoint...): 세이브 포인트(프로그램 꺼질 때, 데이터 마지막 부분 저장)
    .trigger: 1분 주기
    .start() 시작
    """
    query = ohlcv_1m.writeStream \
        .outputMode("update") \
        .format("console") \
        .option("truncate", False) \
        .option("checkpointLocation", "/tmp/checkpoint-preprocess-1m") \
        .trigger(processingTime="1 minute") \
        .start()

    query.awaitTermination() # 끝날때까지 대기 (사용자가 종료 전까지 진행)글글


if __name__ == "__main__":
    main()
