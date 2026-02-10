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
        .getOrCreate()

def read_from_kafka(spark, topic, starting_offsets="latest"):
    """Kafka에서 데이터 읽기 (재사용 가능)"""
    return spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "kafka:29092") \
        .option("subscribe", topic) \
        .option("startingOffsets", starting_offsets) \
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
    spark = create_spark_session("BinanceDepthReader")
    
    # Kafka 읽기
    kafka_df = read_from_kafka(spark, "binance-depth")
    
    # 파싱
    parsed_df = parse_depth_data(kafka_df)
    
    # 출력
    query = parsed_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .trigger(processingTime='10 seconds') \
        .start()
    
    query.awaitTermination()

if __name__ == "__main__":
    main()