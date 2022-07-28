# Chord (DHT)
This repository implement a simple version of the [Chord](https://en.wikipedia.org/wiki/Chord_(peer-to-peer)) algorithm.
The provided code already setups the ring network properly.
1. Supports Node Joins
2. Finds the correct successor for a node
3. Run Stabilize periodically to correct the network

## Course
This project was developed under the Distributed Computing course of [University of Aveiro](https://www.ua.pt/).

## Installation
* Clone the repository:
```console
$ git clone https://github.com/leo-dsf/Chord_DHT
```
* Install requirements:
```console
$ pip install -r requirements.txt
```

## Running the example
Run in two different terminal:
* DHT (setups a Chord DHT):
```console
$ python3 DHT.py
```
* Example (put and get objects from the DHT):
```console
$ python3 example.py
```

## References
[Original Paper](https://pdos.csail.mit.edu/papers/ton:chord/paper-ton.pdf).

## Authors
* **Leonardo Flórido**: [leo-dsf](https://github.com/leo-dsf)
* **Gabriel Hall**: [GabrielHall02](https://github.com/GabrielHall02)

## License
This project is licensed under the [MIT License](LICENSE).
