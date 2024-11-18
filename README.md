# Dev.Space

## Basic Usage
Desktop(PC) is server. Client could be anything, but in here it will be microprocessor or single_board_computer like raspberry pi pico, raspberry pi 4, ASUS Tinkerboard, etc.
> * PC running env
>    * Windows 11, Rust, Python needed
> * IoT
>    * Raspberry Pi 4

At first, run the "iced_gui" with cargo run. 
```bash
git clone https://github.com/Jang707/Dev.Space
cd Dev.Space/rust/default/iced_gui
cargo run
```
After that run the "test_socket.py" at the raspberry pi 4.
```bash
git clone https://github.com/Jang707/Dev.Space
cd Dev.Space/python/default/raspberry_pi_4
### After resolve all dependencies ###
python test_socket.py
```

