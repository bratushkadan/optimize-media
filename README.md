# Optimize Media (MacOS)

## TODO

- [ ] Options for:
  - [ ] Recursive discovery
  - [ ] Preserving input file's directory
  - [ ] Removing input file once the conversion is complete

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

## Video Optimization

Soon<sup>TM</sup>
