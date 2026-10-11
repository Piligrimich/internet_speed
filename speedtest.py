#!/usr/bin/env python3
"""Measure download speed with 10 sequential HTTP GET requests."""

import argparse
import math
import sys
from http.client import HTTPException
from time import perf_counter
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

REQUEST_COUNT = 10
CHUNK_SIZE = 64 * 1024
BYTES_PER_MB = 1_000_000


def http_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        valid = parsed.scheme in {"http", "https"} and parsed.hostname
        parsed.port  # Validate the port, if supplied.
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Некорректный URL") from exc
    if not valid:
        raise argparse.ArgumentTypeError("Укажите полный HTTP(S) URL")
    return value


def positive_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Таймаут должен быть числом") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise argparse.ArgumentTypeError("Таймаут должен быть конечным числом > 0")
    return timeout


def download(url: str, timeout: float) -> tuple[int, float]:
    request = Request(url, headers={
        "Accept-Encoding": "identity",
        "Cache-Control": "no-cache",
        "User-Agent": "InternetSpeedMeter/1.0",
    })
    downloaded = 0
    started = perf_counter()
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError(f"Ожидался HTTP 200, получен HTTP {response.status}")
        expected_size = response.headers.get("Content-Length")
        while chunk := response.read(CHUNK_SIZE):
            downloaded += len(chunk)
        elapsed = perf_counter() - started

        # Content-Length is optional; count actual bytes in either case.
        if expected_size is not None and downloaded != int(expected_size):
            raise ValueError("Ответ оборвался: скачан не весь файл")
    if downloaded == 0:
        raise ValueError("Сервер вернул пустой файл")
    return downloaded, elapsed


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Замер скорости: 10 последовательных скачиваний файла."
    )
    parser.add_argument("url", type=http_url, help="Прямая HTTP(S) ссылка на файл")
    parser.add_argument(
        "--timeout", type=positive_timeout, default=30.0,
        help="Таймаут сетевой операции в секундах (по умолчанию: 30)",
    )
    args = parser.parse_args()

    total_bytes = 0
    total_seconds = 0.0
    try:
        for number in range(1, REQUEST_COUNT + 1):
            size, seconds = download(args.url, args.timeout)
            total_bytes += size
            total_seconds += seconds
            print(f"{number:2}/{REQUEST_COUNT}: {seconds:.3f} с, {size} байт")
    except (URLError, OSError, HTTPException, ValueError) as exc:
        print(f"Ошибка запроса {number}/{REQUEST_COUNT}: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nЗамер прерван.", file=sys.stderr)
        return 130

    speed_mb = total_bytes / total_seconds / BYTES_PER_MB
    print(f"\nСреднее время запроса: {total_seconds / REQUEST_COUNT:.3f} с")
    print(f"Всего скачано: {total_bytes} байт ({total_bytes / BYTES_PER_MB:.3f} МБ)")
    print(f"Скорость: {speed_mb:.3f} МБ/с ({speed_mb * 8:.3f} Мбит/с)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
