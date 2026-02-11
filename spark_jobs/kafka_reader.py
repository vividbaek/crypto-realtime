# spark_jobs/kafka_reader.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, get_json_object

def create_spark_session(app_name="BinanceProcessor"):
    """Spark 세션 생성 (재사용 가능)"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1") \
        .config("spark.sql.streaming.checkpointLocation", f"/tmp/checkpoint-{app_name}") \
        .config("spark.driver.extraJavaOptions", "-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties") \
        .config("spark.executor.extraJavaOptions", "-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties") \
        .getOrCreate()

def read_from_kafka(spark, topic, starting_offsets="latest"):
    """Kafka에서 데이터 읽기 (재사용 가능)"""
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

def parse_depth_data(df):
    """Depth 데이터 파싱 (재사용 가능)"""
    return df.select(
        get_json_object(col("value").cast("string"), "$.symbol").alias("symbol"),
        get_json_object(col("value").cast("string"), "$.data.b[0][0]").cast("double").alias("bid_price"),
        get_json_object(col("value").cast("string"), "$.data.a[0][0]").cast("double").alias("ask_price"),
        col("timestamp").alias("kafka_timestamp")
    )

def main():
    import time
    
    spark = create_spark_session("BinanceDepthReader")
    
    # Kafka가 완전히 준비될 때까지 대기 (Coordinator 초기화 대기)
    print("⏳ Kafka Consumer Group Coordinator 초기화 대기 중... (30초)")
    time.sleep(30)
    
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