"""
Binance kline_1m 토픽 구독 → 파싱 후 콘솔 출력.
우리가 aggTrade로 만든 1분봉(stream_preprocess)과 비교용.

실행: ./scripts/start-spark-job.sh kline
"""
import time
from pyspark.sql.functions import from_unixtime, col
from kafka_reader import create_spark_session, read_from_kafka, parse_kline_data


def main():
    spark = create_spark_session("BinanceKlineConsole")

    print("⏳ Kafka 연결 전 대기 (5초)...")
    time.sleep(5)

    print("📥 binance-kline(Binance 1분봉) 구독 중...")
    kafka_df = read_from_kafka(spark, "binance-kline", starting_offsets="latest")

    parsed = parse_kline_data(kafka_df)
    # window_start_sec → timestamp 컬럼으로 보기 좋게
    with_ts = parsed.withColumn(
        "window_start",
        from_unixtime(col("window_start_sec")).cast("timestamp")
    ).select(
        "window_start", "symbol", "open", "high", "low", "close", "volume", "trades", "is_candle_closed"
    )

    print("🚀 Binance 1분봉 스트리밍 (1분마다 트리거)...")
    query = with_ts.writeStream \
        .outputMode("append") \
        .format("console") \
        .option("truncate", False) \
        .option("checkpointLocation", "/tmp/checkpoint-kline-console") \
        .trigger(processingTime="1 minute") \
        .start()

    query.awaitTermination()


if __name__ == "__main__":
    main()
