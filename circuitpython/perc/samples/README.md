https://github.com/alex-esc/sample-pi
`for i in *.flac; do ffmpeg -i "$i" -sample_fmt s16 -ar 44100 "${i%.*}.wav"; done`
