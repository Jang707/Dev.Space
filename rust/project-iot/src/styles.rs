use iced::{Theme, Color};
use iced::widget::{container, button};
use std::fmt::Display;
use crate::theme;
use crate::messages::Choice;

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

impl Display for Choice {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Choice::Scenario1 => write!(f,"Scenario 1"),
            Choice::Scenario2 => write!(f,"Scenario 2"),
            Choice::Scenario3 => write!(f,"Scenario 3"),
            Choice::Scenario4 => write!(f,"Scenario 4"),
            Choice::Scenario5 => write!(f,"Scenario 5"),
            Choice::Scenario6 => write!(f,"Scenario 6"),
            Choice::Scenario7 => write!(f,"Scenario 7"),
            Choice::Scenario8 => write!(f,"Scenario 8"),
        }
    }
}
// Dropdown END