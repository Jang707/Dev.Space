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
    let (sender, receiver) = mpsc::channel();
    {
        let mut sender_ref = SENDER.lock().unwrap();
        *sender_ref = Some(sender);
    }

    MonitoringGui::run(iced::Settings::with_flags(receiver))
}

#[derive(Debug)]
struct ScrollState {
    viewport: Option<scrollable::Viewport>,  // Option으로 변경
    scrolled_to_bottom: bool,
}

impl Default for ScrollState {
    fn default() -> Self {
        Self {
            viewport: None,
            scrolled_to_bottom: true,
        }
    }
}

struct MonitoringGui {
    log_messages: Vec<String>,
    is_normal: bool,
    python_server: Option<PyObject>,
    receiver: mpsc::Receiver<String>,
    scroll_state: ScrollState,
}

#[derive(Debug, Clone)]
enum Message {
    NormalCreation,
    AbnormalCreation,
    CheckIncoming,
    Scrolled(scrollable::Viewport),
    AutoScroll,
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
            log_messages: vec![String::from("Application started")],
            is_normal: true,
            python_server: None,
            receiver,
            scroll_state: ScrollState::default(),
        };

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
        match message {
            Message::NormalCreation => {
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(
                    format!("{} Normal Creation button is pressed.", current_time)
                );
                self.is_normal = true;
                self.scroll_state.scrolled_to_bottom = true;
                Command::perform(async {}, |_| Message::AutoScroll)
            }
            Message::AbnormalCreation => {
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(
                    format!("{} Abnormal Creation button is pressed.", current_time)
                );
                self.is_normal = false;
                self.scroll_state.scrolled_to_bottom = true;
                Command::perform(async {}, |_| Message::AutoScroll)
            }
            Message::CheckIncoming => {
                let mut received = false;
                while let Ok(data) = self.receiver.try_recv() {
                    self.log_messages.push(data);
                    received = true;
                    
                    // 로그 메시지가 1000개를 초과하면 가장 오래된 메시지를 제거
                    while self.log_messages.len() > 1000 {
                        self.log_messages.remove(0);
                    }
                }
                if received {
                    self.scroll_state.scrolled_to_bottom = true;
                    Command::perform(async {}, |_| Message::AutoScroll)
                } else {
                    Command::none()
                }
            }
            Message::Scrolled(viewport) => {
                self.scroll_state.viewport = Some(viewport);
                self.scroll_state.scrolled_to_bottom = viewport.relative_offset().y > 0.99;
                Command::none()
            }
            Message::AutoScroll => {
                // 새 메시지가 추가되었을 때 자동 스크롤
                if self.scroll_state.scrolled_to_bottom {
                    if let Some(_) = &self.scroll_state.viewport {
                        // 현재 뷰포트의 상태를 유지하면서 스크롤
                        self.scroll_state.scrolled_to_bottom = true;
                    }
                }
                Command::none()
            }
        }
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
        let log_content = column(
            self.log_messages
                .iter()
                .map(|message| {
                    container(text(message).size(14))
                        .width(Length::Fill)
                        .padding(2)
                        .style(iced::theme::Container::Transparent)
                        .into()
                })
                .collect()
        )
        .spacing(0)
        .width(Length::Fill);

        let monitoring_area = scrollable(
            container(log_content)
                .width(Length::Fill)
                .padding(10)
                .style(iced::theme::Container::Custom(Box::new(MonitoringArea)))
        )
        .height(Length::Fixed(300.0))
        .on_scroll(Message::Scrolled)
        .id(scrollable::Id::new("log_scroll")); // 스크롤 ID 추가

        let mut content = column![
            button_row,
            status_row,
            monitoring_area,
        ]
        .padding(20)
        .spacing(10);

        // 자동 스크롤이 활성화되어 있으면 스크롤을 최하단으로
        if self.scroll_state.scrolled_to_bottom {
            content = content.push(iced::widget::Space::new(
                Length::Shrink,
                Length::Fixed(0.0),
            ));
        }

        content.into()
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

// 스타일 구현
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
            background: Some(iced::Background::Color([1.0, 1.0, 1.0].into())),
            border_radius: 4.0.into(),
            ..Default::default()
        }
    }
}