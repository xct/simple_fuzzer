# Simple Fuzzer

Basic educational coverage driven fuzzer. Accompanying blog post: [Building a simple coverage based fuzzer for binary code](https://vulndev.io/2019/06/howto_python_coverage_based_fuzzing.html).

## Installation

* build dynamorio somewhere
* adjust *dynamorioHOME* in fuzz.py

## Usage

* **Make sure you disable ASLR** (`echo 0 | sudo tee /proc/sys/kernel/randomize_va_space`)
* Create a directory with seed files (can be just one file containing arbitrary content)
* Run `python3 fuzz.py working_directory seed_directory 'target_binary arguments'`
* Filename arguments can be given by replacing their filename with '@@'


## Troubleshooting

Building Dynamorio:

I noticed that on kali linux the dynamorio build process is failing due to warning treatment in newer gcc versions. Running the following command on the source directory will let it build:

```bash
find . -type f -exec sed -i 's/-Wall/-Wno-attribute-alias -Wno-stringop-overflow/g' {} +
```