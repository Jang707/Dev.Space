use iced::widget::{button, column, container, row, scrollable, text};
use iced::{Element, Length, Sandbox, Settings};
use chrono::Local;

pub fn main() -> iced::Result {
    MonitoringGui::run(Settings::default())
}

#[derive(Default)]
struct MonitoringGui {
    log_messages: String,
    is_normal: bool,
}

#[derive(Debug, Clone)]
enum Message {
    NormalCreation,
    AbnormalCreation,
}

impl Sandbox for MonitoringGui {
    type Message = Message;

    fn new() -> Self {
        Self {
            log_messages: String::from("Application started"),
            is_normal: true,
        }
    }

    fn title(&self) -> String {
        String::from("Monitoring Application")
    }

    fn update(&mut self, message: Message) {
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
}

// 커스텀 스타일
struct GreenIndicator;
struct RedIndicator;
struct MonitoringArea;

impl container::StyleSheet for GreenIndicator {
    type Style = iced::Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color([0.0, 1.0, 0.0].into())),
            border_radius: 2.0.into(),
            ..Default::default()
        }
    }
}

impl container::StyleSheet for RedIndicator {
    type Style = iced::Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            background: Some(iced::Background::Color([1.0, 0.0, 0.0].into())),
            border_radius: 2.0.into(),
            ..Default::default()
        }
    }
}

impl container::StyleSheet for MonitoringArea {
    type Style = iced::Theme;

    fn appearance(&self, _style: &Self::Style) -> container::Appearance {
        container::Appearance {
            border_width: 1.0,
            border_color: [0.8, 0.8, 0.8].into(),
            ..Default::default()
        }
    }
}