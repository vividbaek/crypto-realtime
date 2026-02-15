# spark_jobs/aggtrade_processor.py
"""
Binance Aggregate Trade 데이터 처리 및 1분봉 집계

Kafka binance-aggtrade 토픽에서 aggTrade 데이터를 읽어
1분 단위로 OHLCV(시가/고가/저가/종가/거래량) 캔들을 생성합니다.
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, get_json_object, from_unixtime, window,
    first, last, max as spark_max, min as spark_min, sum as spark_sum, count
)
import time


def create_spark_session(app_name="AggTradeProcessor"):
    """Spark 세션 생성"""
    return SparkSession.builder \
        .appName(app_name) \
        .config("spark.jars.packages", 
                "org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.1") \
        .config("spark.sql.streaming.checkpointLocation", f"/tmp/checkpoint-{app_name}") \
        .config("spark.driver.extraJavaOptions", "-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties") \
        .config("spark.executor.extraJavaOptions", "-Dlog4j.configuration=file:/opt/spark/work-dir/log4j.properties") \
        .getOrCreate()


def read_from_kafka(spark, topic="binance-aggtrade", starting_offsets="latest"):
    """Kafka에서 aggTrade 데이터 읽기"""
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


def parse_aggtrade_data(df):
    """
    aggTrade 데이터 파싱
    
    데이터 구조:
    {
      "symbol": "BTCUSDT",
      "data": {
        "e": "aggTrade",
        "s": "BTCUSDT", 
        "a": 5933014,       // Aggregate trade ID
        "p": "68970.50",    // Price
        "q": "1.234",       // Quantity
        "f": 100,           // First trade ID
        "l": 105,           // Last trade ID
        "T": 1739561025000, // Trade time (ms)
        "m": true           // Is buyer maker?
      }
    }
    """
    return df.select(
        get_json_object(col("value").cast("string"), "$.symbol").alias("symbol"),
        get_json_object(col("value").cast("string"), "$.data.a").cast("long").alias("trade_id"),
        get_json_object(col("value").cast("string"), "$.data.p").cast("double").alias("price"),
        get_json_object(col("value").cast("string"), "$.data.q").cast("double").alias("quantity"),
        (get_json_object(col("value").cast("string"), "$.data.T").cast("long") / 1000).cast("timestamp").alias("trade_time"),
        get_json_object(col("value").cast("string"), "$.data.m").cast("boolean").alias("is_buyer_maker"),
        col("timestamp").alias("kafka_timestamp")
    )


def aggregate_to_1min_candle(parsed_df):
    """
    1분봉 캔들 생성 (OHLCV)
    
    Returns:
        DataFrame with columns:
        - window_start: 캔들 시작 시각
        - window_end: 캔들 종료 시각
        - symbol: 심볼
        - open: 시가 (첫 거래 가격)
        - high: 고가
        - low: 저가
        - close: 종가 (마지막 거래 가격)
        - volume: 거래량
        - trades: 거래 횟수
        - buy_volume: 매수 거래량 (taker buy)
        - sell_volume: 매도 거래량 (taker sell)
    """
    # 1분 윈도우로 그룹화하여 집계
    candle_df = parsed_df \
        .withWatermark("trade_time", "1 minute") \
        .groupBy(
            window(col("trade_time"), "1 minute"),
            col("symbol")
        ) \
        .agg(
            first("price").alias("open"),
            spark_max("price").alias("high"),
            spark_min("price").alias("low"),
            last("price").alias("close"),
            spark_sum("quantity").alias("volume"),
            count("*").alias("trades"),
            spark_sum(
                col("quantity").cast("double") * (1 - col("is_buyer_maker").cast("int"))
            ).alias("buy_volume"),
            spark_sum(
                col("quantity").cast("double") * col("is_buyer_maker").cast("int")
            ).alias("sell_volume")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            col("symbol"),
            col("open").cast("double"),
            col("high").cast("double"),
            col("low").cast("double"),
            col("close").cast("double"),
            col("volume").cast("double"),
            col("trades").cast("long"),
            col("buy_volume").cast("double"),
            col("sell_volume").cast("double")
        )
    
    return candle_df


def main():
    print("=" * 80)
    print("  🚀 Binance AggTrade Processor")
    print("=" * 80)
    print("  📊 기능: aggTrade → 1분봉 OHLCV 집계")
    print("  📥 입력: Kafka binance-aggtrade 토픽")
    print("  📤 출력: 콘솔 (1분마다)")
    print("=" * 80)
    print()
    
    # Spark 세션 생성
    spark = create_spark_session("AggTradeProcessor")
    
    # Kafka Consumer Group Coordinator 초기화 대기
    print("⏳ Kafka Consumer Group Coordinator 초기화 대기 중... (30초)")
    time.sleep(30)
    
    # Kafka에서 데이터 읽기
    print("📥 Kafka에서 aggTrade 데이터 읽기 시작...")
    kafka_df = read_from_kafka(spark, "binance-aggtrade", starting_offsets="earliest")
    
    # aggTrade 데이터 파싱
    print("🔍 aggTrade 데이터 파싱 중...")
    parsed_df = parse_aggtrade_data(kafka_df)
    
    # 1분봉 캔들 집계
    print("📊 1분봉 캔들 집계 시작...")
    candle_df = aggregate_to_1min_candle(parsed_df)
    
    # 결과 출력 (1분마다 배치 처리)
    print("🚀 스트리밍 쿼리 시작... (1분마다 캔들 출력)")
    print("=" * 80)
    print()
    
    query = candle_df.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", "false") \
        .trigger(processingTime='10 seconds') \
        .start()
    
    query.awaitTermination()


if __name__ == "__main__":
    main()
