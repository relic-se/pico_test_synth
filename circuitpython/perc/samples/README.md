# Percussion Samples

Sourced from: https://github.com/alex-esc/sample-pi

With `ffmpeg` installed, use the following bash command within the `samples` directory to convert original .flac audio files to the appropriate format (mono 16-bit signed WAV): `for i in *.flac; do ffmpeg -i "$i" -sample_fmt s16 -ar 44100 -ac 1 "${i%.*}.wav"; done`.
