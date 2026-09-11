# Optimize Media (MacOS)

## TODO

- [ ] Options for:
  - [ ] Recursive discovery
  - [ ] Preserving input file's directory
  - [ ] Removing input file once the conversion is complete
- [ ] Check if `opus` file audio format works on iOS / iPadOS (`ogg` doesn't IRRC)

## Common Dependencies

- Python 3 – v3.11+

## Images Optimization

> Why *webp*?

All the images are converted to *webp* format as it appears to be portable and efficient for storing and distributing images.
Quality loss is also minimal when using *webp*.

*webp* offers the best balance between the quality/portability.

> Why quality `20` of webp images?

This number seems to be the sweet spot for the quality retention / image storing size, as the difference between the lossless and converted -> compressed image is very hard to spot, it mainly has to deal with the reduction of colour palette on the image, which is nearly impossible to spot if you're not using extreme zooming.

### Images Optimization Dependencies

```sh
brew install libheif webp
```

## Audio Optimization

### Anki

Optimizing media for Anki is pretty straightforward.

Speech survives brutal compression fine. 32 kpbs target is more than enough.

Target format is `opus`. Best format: Opus (~10x smaller than 128k MP3, sounds better than MP3 at same bitrate), it's arguably the best lossy format available. The only downside is that it might be unsupported on some devices / operating systems.

#### Dependencies

```sh
brew install ffmpeg
```

### ASMR / Old music with lower bitrates

Soon<sup>TM</sup>

## Video Optimization

Soon<sup>TM</sup>
