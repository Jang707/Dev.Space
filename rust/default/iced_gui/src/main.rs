#![allow(non_ascii_idents)]
use iced::widget::{container, scrollable, text, mouse_area, Button, Column, Row, Text};
use iced::widget::{button, row, column};
use iced::{executor, Application, Command, Element, Length, Subscription, Theme, Color};
use iced::Font;
//use iced::Alignment;
// 드롭다운 메뉴의 위치를 지정하는 타입 입니다. 현재는 구현되지 않았지만 향후 드롭다운 위치 조정에 사용될 수 있습니다.
/*
#[derive(Debug, Clone)]
enum Position{
    Relative { x: f32, y: f32 },
    Absolute { x: f32, y: f32 },
}
 */
use chrono::Local;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use std::sync::mpsc;
use std::sync::{Arc, Mutex};
use std::fmt::Display;
use std::process::Command as ProcessCommand;
use tokio::spawn;
use std::path::Path;
use std::process::Child;
// for terminate process
use std::io::{BufRead, BufReader, Write};
use std::process::Stdio;
use std::sync::atomic::{AtomicU32, Ordering};
static CURRENT_PID: AtomicU32 = AtomicU32::new(0);

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

#[derive(Debug, Clone)]
struct DropdownState {
    selected: Choice,
    is_expanded: bool,
    position: Position,
}

#[derive(Debug, Clone)]
enum Position {
    Relative { x: f32, y: f32 },
    Absolute { x: f32, y: f32 },
}

struct MonitoringGui {
    log_messages: Vec<LogMessage>,
    is_normal: bool,
    python_server: Option<PyObject>,
    receiver: mpsc::Receiver<String>,
    scroll_state: ScrollState,
    auto_scroll: bool,
    // for Dropdown
    dropdown_state: DropdownState,
    // Dropdown END
    current_script: Option<String>,     // 현재 실행중인 스크립트 경로
    script_running: bool,               // 스크립트 실행 상태 확인용
    current_process: Option<Child>,     // 현재 실행중인 프로세스(스크립트)
}

#[derive(Clone, Debug, Default)]
enum Choice{
    #[default]
    Scenario1,
    Scenario2,
    Scenario3,
    Scenario4,
    Scenario5,
    Scenario6,
    Scenario7,
    Scenario8,
}
const CHOICES: [Choice; 8] = [
    Choice::Scenario1,
    Choice::Scenario2,
    Choice::Scenario3,
    Choice::Scenario4,
    Choice::Scenario5,
    Choice::Scenario6,
    Choice::Scenario7,
    Choice::Scenario8,
];

#[derive(Debug, Clone)]
enum Message {
    NormalCreation,
    AbnormalCreation,
    CheckIncoming,
    Scrolled(scrollable::Viewport),
    AutoScroll,
    ToggleAutoScroll,
    // Dropdown
    DropdownSelect(Choice),
    DropdownToggle,
    DropdownOutsideClick,
    // Dropdown END
    ScriptExecutionStarted(String),     // 스크립트 실행 시작 - 파일 경로 포함
    ScriptExecutionSuccess(String),     // 스크립트 실행 성공 - 출력 메시지 포함
    ScriptExecutionError(String),       // 스크립트 실행 실패 - 에러 메시지 포함
    TerminateScenario,                  // 시나리오 종료 버튼 클릭 시
    ScriptTerminationSuccess(String),   // 스크립트 종료 성공 - 종료된 스크립트 경로 포함
    ScriptTerminationError(String),     // 스크립트 종료 실패 - 에러 메시지 포함
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
    // 파이썬 코드 실행 메서드 : execute_script, handle_script_completion
    fn execute_script(&mut self, is_normal: bool) -> Command<Message> {
        let script_path = self.dropdown_state.selected.get_script_path(is_normal);
            
        if self.script_running {
            return Command::perform(
                async { format!("Another script is already running. Please wait.") },
                Message::ScriptExecutionError,
            );
        }
    
        if !Path::new(&script_path).exists() {
            return Command::perform(
                async move { format!("Script file not found: {}", script_path) },
                Message::ScriptExecutionError,
            );
        }
        
        match ProcessCommand::new("python")
            .arg(&script_path)
            .stdin(Stdio::piped())  // stdin 파이프 추가
            .spawn() {
                Ok(child) => {
                    self.current_process = Some(child);
                    self.current_script = Some(script_path.clone());
                    self.script_running = true;
                    
                    Command::perform(
                        async move { format!("Successfully started script: {}", script_path) },
                        Message::ScriptExecutionSuccess
                    )
                },
                Err(e) => Command::perform(
                    async move { format!("Failed to execute script: {}", e) },
                    Message::ScriptExecutionError
                )
        }
    }
    
    fn handle_script_completion(&mut self, _success: bool, _message: String) {
        //self.script_running = false;
        //self.current_script = None;
    }

    fn terminate_script(&mut self) -> Command<Message> {
        if let Some(child) = &mut self.current_process {
            if let Some(stdin) = child.stdin.as_mut() {
                match writeln!(stdin, "rs202300219928scenarioDONE") {
                    Ok(_) => {
                        self.reset_process_state();
                        Command::perform(
                            async { String::from("Termination signal sent successfully") },
                            Message::ScriptTerminationSuccess
                        )
                    },
                    Err(e) => Command::perform(
                        async move { format!("Failed to send termination signal: {}", e) },
                        Message::ScriptTerminationError
                    )
                }
            } else {
                Command::perform(
                    async { String::from("Failed to get stdin handle") },
                    Message::ScriptTerminationError
                )
            }
        } else {
            Command::perform(
                async { String::from("No running script to terminate") },
                Message::ScriptTerminationError
            )
        }
    }

    // 프로세스 상태 초기화를 위한 helper 함수
    fn reset_process_state(&mut self) {
        self.current_process = None;
        self.current_script = None;
        self.script_running = false;
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
            dropdown_state: DropdownState{
                selected: Choice::default(),
                is_expanded: false,
                position: Position::Relative { x:0.0, y:0.0},
            },
            // 파이썬 코드 실행용 필드 초기화.
            current_script: None,
            script_running: false,
            current_process: None,
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
                // 파이썬 스크립트 실행 명령
                Command::batch(vec![
                    self.execute_script(true),
                    Command::perform(async {}, |_| Message::AutoScroll)
                ])
            }
            Message::AbnormalCreation => {
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(LogMessage {
                    content: format!("{} Abnormal Creation button is pressed.", current_time),
                    log_type: LogType::Normal
                });
                self.is_normal = false;
                self.scroll_state.scrolled_to_bottom = true;
                // 파이썬 스크립트 실행 명령
                Command::batch(vec![
                    self.execute_script(false),
                    Command::perform(async {}, |_| Message::AutoScroll)
                ])
            }
            // 파이썬 스크립트 실행 핸들러
            Message::ScriptExecutionStarted(path) => {
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(LogMessage {
                    content: format!("{} Starting script execution: {}", current_time, path),
                    log_type: LogType::Normal
                });
                Command::none()
            }
            // 파이썬 스크립트 실행 성공시 메시지 핸들러
            Message::ScriptExecutionSuccess(message) => {
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(LogMessage {
                    content: format!("{} {}", current_time, message),
                    log_type: LogType::Normal
                });
                self.handle_script_completion(true, message);
                Command::none()
            }
            // 파이썬 스크립트 실행 실패시 메시지 핸들러
            Message::ScriptExecutionError(error) => {
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(LogMessage {
                    content: format!("{} Error: {}", current_time, error),
                    log_type: LogType::Normal
                });
                self.handle_script_completion(false, error);
                Command::none()
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
            // Dropdown
            Message::DropdownSelect(choice) => {
                self.dropdown_state.selected = choice.clone();
                self.dropdown_state.is_expanded = false;
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(LogMessage {
                    content: format!("{} {} is selected.", current_time, choice),
                    log_type: LogType::Normal
                });
                Command::perform(async {}, |_| Message::AutoScroll)
            }
            Message::DropdownToggle => {
                self.dropdown_state.is_expanded = !self.dropdown_state.is_expanded;
                Command::none()
            }
            Message::DropdownOutsideClick => {
                if self.dropdown_state.is_expanded{
                    self.dropdown_state.is_expanded = false;
                }
                Command::none()
            },
            // Dropdown END
            // 파이썬 스크립트 종료를 위한 메시지 처리.
            Message::TerminateScenario => {
                if self.script_running {
                    let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                    self.log_messages.push(LogMessage {
                        content: format!("{} Attempting to terminate current scenario...", current_time),
                        log_type: LogType::Normal
                    });
                    self.terminate_script()
                } else {
                    Command::none()
                }
            },
            Message::ScriptTerminationSuccess(message) => {
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(LogMessage {
                    content: format!("{} {}", current_time, message),
                    log_type: LogType::Normal
                });
                self.reset_process_state();
                Command::none()
            },
            Message::ScriptTerminationError(error) => {
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(LogMessage {
                    content: format!("{} Error: {}", current_time, error),
                    log_type: LogType::Normal
                });
                Command::none()
            },
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
            if self.script_running {
                button_style("Terminate Scenario")
                    .on_press(Message::TerminateScenario)
            } else {
                button(
                    text("Terminate Scenario")
                        .size(16)
                        .style(iced::theme::Text::Color(Color {
                            a: 0.5,
                            ..theme::TEXT
                        }))
                )
                .padding([8, 16])
                .style(iced::theme::Button::Custom(Box::new(DisabledButton)))
            }
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

        // Dropdown
        let build_dropdown = || {
            let selected_text: Element<Message> = text(format!("Selected: {}", self.dropdown_state.selected))
                .size(16)
                .style(iced::theme::Text::Color(theme::TEXT))
                .into();
        
            let arrow_text: Element<Message> = text("▼")
                .size(16)
                .style(iced::theme::Text::Color(theme::TEXT))
                .into();
        
            let dropdown_button = button(
                row![
                    selected_text,
                    arrow_text
                ]
                .spacing(10)
            )
            .style(iced::theme::Button::Custom(Box::new(DropdownButton)))
            .padding([8, 16])
            .on_press(Message::DropdownToggle);
        
            let dropdown_content = if self.dropdown_state.is_expanded {
                container(
                    column(
                        CHOICES.iter().map(|choice| {
                            let choice_text: Element<Message> = text(choice.to_string())
                                .size(16)
                                .style(iced::theme::Text::Color(theme::TEXT))
                                .into();
                                
                            button(choice_text)
                                .style(iced::theme::Button::Custom(Box::new(DropdownItem)))
                                .padding([8, 16])
                                .width(Length::Fill)
                                .on_press(Message::DropdownSelect(choice.clone()))
                                .into()
                        }).collect()
                    )
                    .spacing(2)
                )
                .style(iced::theme::Container::Custom(Box::new(DropdownList)))
                .width(Length::Fill)
            } else {
                container(column![])
                    .width(Length::Fill)
            };
        
            container(
                column![
                    dropdown_button,
                    dropdown_content
                ]
                .spacing(2)
            )
            .style(iced::theme::Container::Custom(Box::new(DropdownContainer)))
            .width(Length::Fixed(200.0))
        };
        
        let dropdown_container: Element<Message> = if self.dropdown_state.is_expanded {
            mouse_area(container(build_dropdown()))
                .on_press(Message::DropdownOutsideClick)
                .into()
        } else {
            container(build_dropdown())
                .into()
        };
        
        let content = column![
            header,
            dropdown_container,
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

struct DropdownButton;
struct DropdownContainer;
struct DropdownItem;
struct DropdownList;

struct DisabledButton;  // 파일 스크립트 종료 버튼의 비활성화를 위한 기능.

impl button::StyleSheet for CustomButton {
    type Style = Theme;

    fn active(&self, _style: &Self::Style) -> button::Appearance {
        button::Appearance {
            background: Some(iced::Background::Color(theme::SURFACE)),
            border_radius: 6.0.into(),
            border_width: 1.0,
            border_color: theme::ACCENT,
            text_color: theme::TEXT,
            ..Default::default()
        }
    }

    fn hovered(&self, style: &Self::Style) -> button::Appearance {
        let mut active = self.active(style);
        active.background = Some(iced::Background::Color(Color {
            a: 0.8,
            ..theme::ACCENT
        }));
        active
    }
}

impl button::StyleSheet for DropdownButton {
    type Style = Theme;

    fn active(&self, _style: &Self::Style) -> button::Appearance {
        button::Appearance {
            background: Some(iced::Background::Color(theme::SURFACE)),
            border_radius: 6.0.into(),
            border_width: 1.0,
            border_color: theme::ACCENT,
            text_color: theme::TEXT,
            shadow_offset: iced::Vector::new(0.0, 1.0),
            ..Default::default()
        }
    }

    fn hovered(&self, style: &Self::Style) -> button::Appearance {
        let mut active = self.active(style);
        active.border_color = Color {
            a: 0.8,
            ..theme::ACCENT
        };
        active.shadow_offset = iced::Vector::new(0.0, 2.0);
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
// for Dropdown
impl container::StyleSheet for DropdownContainer {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color(theme::SURFACE)),
            border_radius: 6.0.into(),
            border_width: 1.0,
            border_color: theme::ACCENT,
            text_color: Some(theme::TEXT),
            ..Default::default()
        }
    }
}

impl container::StyleSheet for DropdownList {
    type Style = Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color(theme::SURFACE)),
            border_width: 1.0,
            border_color: theme::ACCENT,
            border_radius: 4.0.into(),
            ..Default::default()
        }
    }
}

impl button::StyleSheet for DropdownItem {
    type Style = Theme;

    fn active(&self, _style: &Self::Style) -> button::Appearance {
        button::Appearance {
            background: Some(iced::Background::Color(theme::SURFACE)),
            border_radius: 4.0.into(),
            border_width: 1.0,
            text_color: theme::TEXT,
            ..Default::default()
        }
    }

    fn hovered(&self, _style: &Self::Style) -> button::Appearance {
        button::Appearance {
            background: Some(iced::Background::Color(Color {
                //a: 0.1,
                ..theme::ACCENT
            })),
            border_radius: 4.0.into(),
            border_width: 1.0,
            text_color: theme::TEXT,
            ..Default::default()
        }
    }
}

impl Choice {
    fn get_script_path(&self, is_normal: bool) -> String {
        let base_path = "D:\\Dev.Space\\python\\default\\automation_script\\";
        let script_name = match self {
            Choice::Scenario1 => "scenario1",
            Choice::Scenario2 => "scenario2",
            Choice::Scenario3 => "scenario3",
            Choice::Scenario4 => "scenario4",
            Choice::Scenario5 => "scenario5",
            Choice::Scenario6 => "scenario6",
            Choice::Scenario7 => "scenario7",
            Choice::Scenario8 => "scenario8",
        };
        
        format!("{}{}_{}.py", 
            base_path, 
            script_name, 
            if is_normal { "auto" } else { "abnormal" }
        )
    }
}

impl Display for Choice {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Choice::Scenario1 => write!(f, "Scenario 1"),
            Choice::Scenario2 => write!(f, "Scenario 2"),
            Choice::Scenario3 => write!(f, "Scenario 3"),
            Choice::Scenario4 => write!(f, "Scenario 4"),
            Choice::Scenario5 => write!(f, "Scenario 5"),
            Choice::Scenario6 => write!(f, "Scenario 6"),
            Choice::Scenario7 => write!(f, "Scenario 7"),
            Choice::Scenario8 => write!(f, "Scenario 8"),
        }
    }
}
// Dropdown END

impl button::StyleSheet for DisabledButton {
    type Style = Theme;

    fn active(&self, _style: &Self::Style) -> button::Appearance {
        button::Appearance {
            background: Some(iced::Background::Color(Color {
                a: 0.5,
                ..theme::SURFACE
            })),
            border_radius: 6.0.into(),
            border_width: 1.0,
            border_color: Color {
                a: 0.5,
                ..theme::ACCENT
            },
            text_color: Color {
                a: 0.5,
                ..theme::TEXT
            },
            ..Default::default()
        }
    }

    fn hovered(&self, style: &Self::Style) -> button::Appearance {
        self.active(style)
    }
}