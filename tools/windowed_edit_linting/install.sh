_write_env "CURRENT_FILE" "${CURRENT_FILE:-}"
_write_env "CURRENT_LINE" "${CURRENT_LINE:-0}"
_write_env "WINDOW" "$WINDOW"

/root/python3.11/bin/python3.11 -m pip install flake8
