# CHORD (DHT)

This repository implement a simple version of the [CHORD](https://en.wikipedia.org/wiki/Chord_(peer-to-peer)) algorithm.
The provided code already setups the ring network properly.
1. Supports Node Joins
2. Finds the correct successor for a node
3. Run Stabilize periodically to correct the network


## Running the example
Run in two different terminal:

DHT (setups a CHORD DHT):
```console
$ python3 DHT.py
```
example (put and get objects from the DHT):
```console
$ python3 example.py
```

## References

[original paper](https://pdos.csail.mit.edu/papers/ton:chord/paper-ton.pdf)

## Authors
* **Leonardo Flórido**: [leo-dsf](https://github.com/leo-dsf)
* **Gabriel Hall**: [GabrielHall02](https://github.com/GabrielHall02)

## License
This project is licensed under the [MIT License](LICENSE).