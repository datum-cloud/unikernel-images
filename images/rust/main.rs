//! Default entrypoint: a std-only HTTP server on port 8080. Copy this
//! directory's Dockerfile and Kraftfile to package your own Rust service.

use std::io::{Read, Write};
use std::net::TcpListener;

fn main() {
    let port = std::env::var("PORT").unwrap_or_else(|_| "8080".to_string());
    // [::] is dual-stack (IPv6 plus IPv4-mapped); Datum compute networks are
    // IPv6-only, so an IPv4-only bind is unreachable. Fall back to IPv4 only
    // when the runtime has no IPv6 sockets at all.
    let listener = TcpListener::bind(format!("[::]:{port}"))
        .or_else(|_| TcpListener::bind(format!("0.0.0.0:{port}")))
        .expect("bind");
    println!("listening on :{port}");
    for stream in listener.incoming() {
        let Ok(mut stream) = stream else { continue };
        let mut buf = [0u8; 1024];
        let _ = stream.read(&mut buf);
        let body = r#"{"service":"rust","message":"Hello from Rust on a Datum unikernel"}"#;
        let resp = format!(
            "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
            body.len(),
            body
        );
        let _ = stream.write_all(resp.as_bytes());
    }
}
