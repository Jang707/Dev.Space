use iced::widget::{button, column, container, row, scrollable, text};
use iced::{executor, Element, Length, Command, Application, Theme, Subscription};
use chrono::Local;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use std::sync::mpsc;
use std::sync::{Arc, Mutex};

lazy_static::lazy_static! {
    static ref SENDER: Arc<Mutex<Option<mpsc::Sender<String>>>> = Arc::new(Mutex::new(None));
}

pub fn main() -> iced::Result {
    // Python callback을 위한 채널 생성
    let (sender, receiver) = mpsc::channel();
    {
        let mut sender_ref = SENDER.lock().unwrap();
        *sender_ref = Some(sender);
    }

    // MonitoringGui 실행
    MonitoringGui::run(iced::Settings::with_flags(receiver))
}

struct MonitoringGui {
    log_messages: String,
    is_normal: bool,
    python_server: Option<PyObject>,
    receiver: mpsc::Receiver<String>,
}

#[derive(Debug, Clone)]
enum Message {
    NormalCreation,
    AbnormalCreation,
    CheckIncoming,
    Tick,
}

#[pyfunction]
fn py_callback(data: String) {
    if let Ok(sender_guard) = SENDER.lock() {
        if let Some(sender) = &*sender_guard {
            if let Err(e) = sender.send(data) {
                eprintln!("Failed to send data through channel: {}", e);
            }
        }
    }
}

impl Application for MonitoringGui {
    type Message = Message;
    type Theme = Theme;
    type Executor = executor::Default;
    type Flags = mpsc::Receiver<String>;

    fn new(receiver: Self::Flags) -> (Self, Command<Message>) {
        let instance = Self {
            log_messages: String::from("Application started"),
            is_normal: true,
            python_server: None,
            receiver,
        };

        // Python 모듈 로드 및 서버 시작
        Python::with_gil(|py| {
            let sys = py.import("sys")?;
            let path: &PyTuple = PyTuple::new(py, &["D:/senario/python/default"]);
            sys.getattr("path")?.call_method1("append", path)?;

            let server_module = py.import("Server_socket")?;
            let server = server_module.getattr("TCPServer")?.call0()?;
            
            let callback = wrap_pyfunction!(py_callback)(py)?;
            server.call_method1("set_callback", (callback,))?;
            
            server.call_method0("start")?;
            Ok::<_, PyErr>(())
        }).expect("Failed to initialize Python server");

        (instance, Command::none())
    }

    fn title(&self) -> String {
        String::from("Monitoring Application")
    }

    fn update(&mut self, message: Message) -> Command<Message> {
        let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
        
        match message {
            Message::NormalCreation => {
                self.log_messages = format!(
                    "{}\n{} Normal Creation button is pressed.",
                    self.log_messages, current_time
                );
                self.is_normal = true;
            }
            Message::AbnormalCreation => {
                self.log_messages = format!(
                    "{}\n{} Abnormal Creation button is pressed.",
                    self.log_messages, current_time
                );
                self.is_normal = false;
            }
            Message::CheckIncoming => {
                while let Ok(data) = self.receiver.try_recv() {
                    self.log_messages = format!(
                        "{}\n{}",
                        self.log_messages, data
                    );
                }
            }
            Message::Tick => {
                self.update(Message::CheckIncoming);
            }
        }
        
        Command::none()
    }

    fn view(&self) -> Element<Message> {
        // 버튼 영역
        let button_row = row![
            button("Normal Creation").on_press(Message::NormalCreation),
            button("Abnormal Creation").on_press(Message::AbnormalCreation),
        ]
        .spacing(10);

        // 상태 표시등
        let status_size = 20;
        let normal_indicator = container(text(""))
            .width(Length::Fixed(status_size as f32))
            .height(Length::Fixed(status_size as f32))
            .style(if self.is_normal {
                iced::theme::Container::Custom(Box::new(GreenIndicator))
            } else {
                iced::theme::Container::Transparent
            });

        let abnormal_indicator = container(text(""))
            .width(Length::Fixed(status_size as f32))
            .height(Length::Fixed(status_size as f32))
            .style(if !self.is_normal {
                iced::theme::Container::Custom(Box::new(RedIndicator))
            } else {
                iced::theme::Container::Transparent
            });

        let status_row = row![normal_indicator, abnormal_indicator].spacing(5);

        // 모니터링 영역
        let monitoring_area = scrollable(
            container(text(&self.log_messages))
                .width(Length::Fill)
                .height(Length::Fixed(300.0))
                .style(iced::theme::Container::Custom(Box::new(MonitoringArea)))
        );

        // 전체 레이아웃
        column![
            button_row,
            status_row,
            monitoring_area,
        ]
        .padding(20)
        .spacing(10)
        .into()
    }

    fn subscription(&self) -> Subscription<Message> {
        iced::subscription::unfold(
            "message_checker",
            (),
            |_| async {
                tokio::time::sleep(std::time::Duration::from_millis(100)).await;
                (Message::CheckIncoming, ())
            },
        )
    }
}

// 스타일 구현은 동일하게 유지...

// 스타일 구현은 동일하게 유지
struct GreenIndicator;
struct RedIndicator;
struct MonitoringArea;

impl container::StyleSheet for GreenIndicator {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color([0.0, 1.0, 0.0].into())),
            border_radius: 2.0.into(),
            ..Default::default()
        }
    }
}

impl container::StyleSheet for RedIndicator {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color([1.0, 0.0, 0.0].into())),
            border_radius: 2.0.into(),
            ..Default::default()
        }
    }
}

impl container::StyleSheet for MonitoringArea {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            border_width: 1.0,
            border_color: [0.8, 0.8, 0.8].into(),
            ..Default::default()
        }
    }
}