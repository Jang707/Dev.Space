#![allow(unused)]
fn main() {
    use std::process::Command;
    
    Command::new("python")
        .args(["D:\\Dev.Space\\python\\default\\automation_script\\senario3_auto.py"])
        .spawn()
        .expect("ls command failed to start");
}