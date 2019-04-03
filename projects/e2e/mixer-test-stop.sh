[[ ! -z "$(pgrep gst)" ]] && kill -2 $(pgrep gst)
[[ ! -z "$(pgrep Python)" ]] && kill -9 $(pgrep Python)
