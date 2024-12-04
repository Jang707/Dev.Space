#![allow(non_ascii_idents)]
use iced::widget::{button, column, container, row, scrollable, text};
use iced::{executor, Application, Command, Element, Length, Subscription, Theme, Color};
use iced::Font;
use chrono::Local;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use std::sync::mpsc;
use std::sync::{Arc, Mutex};

const SYSTEM_FONT: Font = Font::with_name("Malgun Gothic");

// Custom color palette for dark theme
mod theme {
    use super::*;
    
    pub const BACKGROUND: Color = Color::from_rgb(
        0x2E as f32 / 255.0,
        0x34 as f32 / 255.0,
        0x40 as f32 / 255.0,
    );
    pub const SURFACE: Color = Color::from_rgb(
        0x3B as f32 / 255.0,
        0x42 as f32 / 255.0,
        0x4F as f32 / 255.0,
    );
    pub const ACCENT: Color = Color::from_rgb(
        0x5E as f32 / 255.0,
        0x81 as f32 / 255.0,
        0xAC as f32 / 255.0,
    );
    pub const TEXT: Color = Color::from_rgb(
        0xF4 as f32 / 255.0,
        0xF4 as f32 / 255.0,
        0xF4 as f32 / 255.0,
    );
    pub const SUCCESS: Color = Color::from_rgb(
        0xA3 as f32 / 255.0,
        0xBE as f32 / 255.0,
        0x8C as f32 / 255.0,
    );
    pub const ERROR: Color = Color::from_rgb(
        0xBF as f32 / 255.0,
        0x61 as f32 / 255.0,
        0x6A as f32 / 255.0,
    );
    pub const SERIAL: Color = Color::from_rgb(
        0x81 as f32 / 255.0,
        0xA1 as f32 / 255.0,
        0xC1 as f32 / 255.0,
    );
}

lazy_static::lazy_static! {
    static ref SENDER: Arc<Mutex<Option<mpsc::Sender<String>>>> = Arc::new(Mutex::new(None));
}

pub fn main() -> iced::Result {
    let (sender, receiver) = mpsc::channel();
    {
        let mut sender_ref = SENDER.lock().unwrap();
        *sender_ref = Some(sender);
    }

    MonitoringGui::run(iced::Settings {
        window: iced::window::Settings {
            size: (800, 600),
            position: iced::window::Position::Centered,
            min_size: Some((400, 300)),
            ..Default::default()
        },
        ..iced::Settings::with_flags(receiver)
    })
}

#[derive(Debug)]
struct ScrollState {
    viewport: Option<scrollable::Viewport>,
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

#[derive(Debug, Clone)]
enum LogType {
    Normal,
    Serial,
    TCP,
}

#[derive(Debug, Clone)]
struct LogMessage {
    content: String,
    log_type: LogType,
}

struct MonitoringGui {
    log_messages: Vec<LogMessage>,
    is_normal: bool,
    python_server: Option<PyObject>,
    receiver: mpsc::Receiver<String>,
    scroll_state: ScrollState,
    auto_scroll: bool,
}

#[derive(Debug, Clone)]
enum Message {
    NormalCreation,
    AbnormalCreation,
    CheckIncoming,
    Scrolled(scrollable::Viewport),
    AutoScroll,
    ToggleAutoScroll,
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

impl MonitoringGui {
    fn parse_log_type(message: &str) -> LogType {
        if message.contains("[Serial]") {
            LogType::Serial
        } else if message.contains("[Server]") {
            LogType::TCP
        } else {
            LogType::Normal
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
            log_messages: vec![LogMessage { 
                content: String::from("Application started"),
                log_type: LogType::Normal
            }],
            is_normal: true,
            python_server: None,
            receiver,
            scroll_state: ScrollState::default(),
            auto_scroll: true,
        };

        Python::with_gil(|py| {
            let sys = py.import("sys")?;
            let path: &PyTuple = PyTuple::new(py, &["D:/Dev.Space/python/default"]);
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
                self.log_messages.push(LogMessage {
                    content: format!("{} Normal Creation button is pressed.", current_time),
                    log_type: LogType::Normal
                });
                self.is_normal = true;
                self.scroll_state.scrolled_to_bottom = true;
                Command::perform(async {}, |_| Message::AutoScroll)
            }
            Message::AbnormalCreation => {
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(LogMessage {
                    content: format!("{} Abnormal Creation button is pressed.", current_time),
                    log_type: LogType::Normal
                });
                self.is_normal = false;
                self.scroll_state.scrolled_to_bottom = true;
                Command::perform(async {}, |_| Message::AutoScroll)
            }
            Message::CheckIncoming => {
                let mut received = false;
                while let Ok(data) = self.receiver.try_recv() {
                    self.log_messages.push(LogMessage {
                        content: data.clone(),
                        log_type: Self::parse_log_type(&data)
                    });
                    received = true;
                    
                    while self.log_messages.len() > 1000 {
                        self.log_messages.remove(0);
                    }
                }
                if received && self.auto_scroll {
                    Command::batch(vec![
                        scrollable::snap_to(
                            scrollable::Id::new("log_scroll"),
                            scrollable::RelativeOffset::END,
                        ),
                        Command::perform(async {}, |_| Message::AutoScroll)
                    ])
                } else {
                    Command::none()
                }
            }
            Message::Scrolled(viewport) => {
                self.scroll_state.viewport = Some(viewport);
                if !self.auto_scroll{
                    self.scroll_state.scrolled_to_bottom = viewport.relative_offset().y >= 0.99;
                }
                Command::none()
            }
            Message::ToggleAutoScroll => {
                self.auto_scroll = !self.auto_scroll;
                if self.auto_scroll {
                    Command::batch(vec![
                        scrollable::snap_to(
                            scrollable::Id::new("log_scroll"), 
                            scrollable::RelativeOffset::END,
                        ),
                        Command::perform(async {},|_| Message::AutoScroll),
                    ])
                } else {
                    Command::none()
                }
            }
            Message::AutoScroll => {
                Command::none()
            }
        }
    }

    fn view(&self) -> Element<Message> {
        let korean_font = Font::with_name("Malgun Gothic");

        let header = column![
            text("TRUST-IOT  Ver.1.0")
                .size(24)
                .font(korean_font)
                .style(iced::theme::Text::Color(theme::TEXT))
                .width(Length::Fill),
            text("사이버 위협의 선제적 대응을 위한 ICS 보안 취약점 분석 기반")
                .size(10)
                .font(korean_font)
                .style(iced::theme::Text::Color(theme::TEXT))
                .width(Length::Fill),
            text("지능형 위협예측과 시뮬레이션 위협검증 수행의 ICS 보안 취약점 분석관리")
                .size(10)
                .font(korean_font)
                .style(iced::theme::Text::Color(theme::TEXT))
                .width(Length::Fill),
            text("ICS 보안 취약점 분석예측 솔루션")
                .size(18)
                .font(korean_font)
                .style(iced::theme::Text::Color(theme::TEXT))
                .width(Length::Fill),
        ]
        .spacing(5)
        .padding(20);

        let button_style = |label: &str| {
            button(
                text(label)
                    .size(16)
                    .style(theme::TEXT)
            )
            .padding([8, 16])
            .style(iced::theme::Button::Custom(Box::new(CustomButton)))
        };

        let button_row = row![
            button_style("Normal Creation").on_press(Message::NormalCreation),
            button_style("Abnormal Creation").on_press(Message::AbnormalCreation),
            button_style(if self.auto_scroll {"Auto Scroll: ON"} else {"Auto Scroll: OFF"})
                .on_press(Message::ToggleAutoScroll),
        ]
        .spacing(15)
        .padding(20);

        let status_size = 24;
        let normal_indicator = container(text(""))
            .width(Length::Fixed(status_size as f32))
            .height(Length::Fixed(status_size as f32))
            .style(if self.is_normal {
                iced::theme::Container::Custom(Box::new(GreenIndicator))
            } else {
                iced::theme::Container::Custom(Box::new(InactiveIndicator))
            });

        let abnormal_indicator = container(text(""))
            .width(Length::Fixed(status_size as f32))
            .height(Length::Fixed(status_size as f32))
            .style(if !self.is_normal {
                iced::theme::Container::Custom(Box::new(RedIndicator))
            } else {
                iced::theme::Container::Custom(Box::new(InactiveIndicator))
            });

        let status_row = row![
            text("Status:").style(theme::TEXT),
            normal_indicator,
            abnormal_indicator
        ]
        .spacing(10)
        .padding(20);

        let log_content = column(
            self.log_messages
                .iter()
                .map(|message| {
                    let text_color = match message.log_type {
                        LogType::Serial => theme::SERIAL,
                        LogType::TCP => theme::ACCENT,
                        LogType::Normal => theme::TEXT,
                    };
                    
                    container(
                        text(&message.content)
                            .size(14)
                            .style(iced::theme::Text::Color(text_color))
                    )
                    .width(Length::Fill)
                    .padding(4)
                    .style(iced::theme::Container::Custom(Box::new(LogEntry)))
                    .into()
                })
                .collect()
        )
        .spacing(2)
        .width(Length::Fill);

        let monitoring_area = scrollable(
            container(log_content)
                .width(Length::Fill)
                .padding(10)
                .style(iced::theme::Container::Custom(Box::new(MonitoringArea)))
        )
        .height(Length::Fixed(400.0))
        .on_scroll(Message::Scrolled)
        .id(scrollable::Id::new("log_scroll"));

        let content = column![
            header,
            button_row,
            status_row,
            monitoring_area,
        ]
        .padding(20)
        .spacing(10);

        container(content)
            .width(Length::Fill)
            .height(Length::Fill)
            .style(iced::theme::Container::Custom(Box::new(DarkContainer)))
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

// Style implementations
struct CustomButton;
struct GreenIndicator;
struct RedIndicator;
struct InactiveIndicator;
struct MonitoringArea;
struct DarkContainer;
struct LogEntry;

impl button::StyleSheet for CustomButton {
    type Style = Theme;

    fn active(&self, _style: &Self::Style) -> button::Appearance {
        button::Appearance {
            background: Some(iced::Background::Color(theme::ACCENT)),
            border_radius: 6.0.into(),
            border_width: 0.0,
            border_color: Color::TRANSPARENT,
            text_color: theme::TEXT,
            shadow_offset: iced::Vector::new(0.0, 2.0),
            ..Default::default()
        }
    }

    fn hovered(&self, style: &Self::Style) -> button::Appearance {
        let mut active = self.active(style);
        // Instead of using lighten(), use a slightly modified color
        let hovered_color = Color {a: theme::ACCENT.a, ..theme::ACCENT };
        active.background = Some(iced::Background::Color(hovered_color));
        active.shadow_offset = iced::Vector::new(0.0, 3.0);
        active
    }
}

impl container::StyleSheet for GreenIndicator {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color(theme::SUCCESS)),
            border_radius: 12.0.into(),
            border_width: 2.0,
            border_color: theme::SUCCESS, // use the same color without darkening
            ..Default::default()
        }
    }
}

impl container::StyleSheet for RedIndicator {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color(theme::ERROR)),
            border_radius: 12.0.into(),
            border_width: 2.0,
            border_color: theme::ERROR, // use the same color without darkening
            ..Default::default()
        }
    }
}

impl container::StyleSheet for InactiveIndicator {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color(theme::SURFACE)),
            border_radius: 12.0.into(),
            border_width: 2.0,
            border_color: theme::SURFACE, // Use the same color without darkening
            ..Default::default()
        }
    }
}

impl container::StyleSheet for MonitoringArea {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color(theme::SURFACE)),
            border_width: 1.0,
            border_color: theme::ACCENT, 
            border_radius: 8.0.into(),
            ..Default::default()
        }
    }
}

impl container::StyleSheet for DarkContainer {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color(theme::BACKGROUND)),
            text_color: Some(theme::TEXT),
            ..Default::default()
        }
    }
}

impl container::StyleSheet for LogEntry {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            text_color: Some(theme::TEXT),
            ..Default::default()
        }
    }
}