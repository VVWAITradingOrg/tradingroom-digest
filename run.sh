#!/bin/bash
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$DIR/.env" ]; then
  echo "找不到 $DIR/.env，请先按说明创建它（写入 DISCORD_TOKEN=你的token）" >&2
  exit 1
fi

set -a
source "$DIR/.env"
set +a

if [ -z "${DISCORD_TOKEN:-}" ]; then
  echo "DISCORD_TOKEN 为空，请检查 .env 文件内容" >&2
  exit 1
fi

exec "$DIR/DiscordChatExporter.Cli" "$@" --token "$DISCORD_TOKEN"
