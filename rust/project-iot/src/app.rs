use iced::widget::{container, scrollable, text, mouse_area, row, button,column, Button, Column, Row};
use iced::{executor, Application, Command, Element, Length, Subscription, Theme};
use iced::Font;
use chrono::Local;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use pyo3::pyfunction;
use std::sync::mpsc;

use crate::messages::{Message, LogType, Choice, CHOICES};
use crate::components::{ScrollState, LogMessage, DropdownState, Position};
use crate::styles::*;
use crate::theme;

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
            dropdown_state: DropdownState{
                selected: Choice::default(),
                is_expanded: false,
                position: Position::Relative { x:0.0, y:0.0},
            },
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
            // Dropdown
            Message::DropdownSelect(choice) => {
                self.dropdown_state.selected = choice.clone();
                self.dropdown_state.is_expanded = false;
                let current_time = Local::now().format("[%Y.%m.%d-%H:%M:%S]").to_string();
                self.log_messages.push(LogMessage {
                    content: format!("{} Scenario {} is selected.", current_time, choice),
                    log_type: LogType::Normal
                });
                Command::none()
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