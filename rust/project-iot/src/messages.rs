// messages.rs
use iced::widget::scrollable;

#[derive(Debug, Clone)]
pub enum Message {
    NormalCreation,
    AbnormalCreation,
    CheckIncoming,
    Scrolled(scrollable::Viewport),
    AutoScroll,
    ToggleAutoScroll,
    DropdownSelect(Choice),
    DropdownToggle,
    DropdownOutsideClick,
}

#[derive(Debug, Clone)]
pub enum LogType {
    Normal,
    Serial,
    TCP,
}

#[derive(Clone, Debug, Default)]
pub enum Choice {
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

impl std::fmt::Display for Choice {
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

pub const CHOICES: [Choice; 8] = [
    Choice::Scenario1,
    Choice::Scenario2,
    Choice::Scenario3,
    Choice::Scenario4,
    Choice::Scenario5,
    Choice::Scenario6,
    Choice::Scenario7,
    Choice::Scenario8,
];