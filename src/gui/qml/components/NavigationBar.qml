// NavigationBar.qml - Sol Navigasyon Menüsü
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Rectangle {
    id: navRoot
    color: (root.currentTheme === "light") ? "#ffffff" : "#121224"

    property int currentIndex: 0
    signal pageSelected(int index)

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 18
        anchors.bottomMargin: 18
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        spacing: 14

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 88
            radius: 18
            color: root.inputBackground
            border.color: root.borderColor

            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12

                Rectangle {
                    Layout.preferredWidth: 56
                    Layout.preferredHeight: 56
                    radius: 16
                    color: root.cardBackground
                    border.color: Material.accent

                    Image {
                        anchors.centerIn: parent
                        source: root.brandingLogoSource
                        width: 38
                        height: 38
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        mipmap: true
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        text: (backend.uiTrigger, backend.getTextWithDefault("app_title", "RenLocalizer"))
                        color: root.mainTextColor
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Label {
                        text: (backend.uiTrigger, backend.getTextWithDefault("app_subtitle", "Ren'Py Translation Tool"))
                        color: root.secondaryTextColor
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            text: (backend.uiTrigger, backend.getTextWithDefault("nav_workspace_label", "Workspace"))
            color: root.secondaryTextColor
            font.pixelSize: 11
            font.bold: true
            font.letterSpacing: 0.6
            leftPadding: 4
        }

        NavButton {
            icon: "🏠"
            label: backend.getTextWithDefault("nav_home", "Home")
            selected: navRoot.currentIndex === 0
            onClicked: {
                navRoot.currentIndex = 0
                navRoot.pageSelected(0)
            }
        }

        NavButton {
            icon: "🛠"
            label: backend.getTextWithDefault("nav_tools", "Tools")
            selected: navRoot.currentIndex === 1
            onClicked: {
                navRoot.currentIndex = 1
                navRoot.pageSelected(1)
            }
        }

        NavButton {
            icon: "📚"
            label: backend.getTextWithDefault("nav_glossary", "Glossary Management")
            selected: navRoot.currentIndex === 2
            onClicked: {
                navRoot.currentIndex = 2
                navRoot.pageSelected(2)
            }
        }

        NavButton {
            icon: "🧠"
            label: backend.getTextWithDefault("nav_cache", "Translation Reuse")
            selected: navRoot.currentIndex === 3
            onClicked: {
                navRoot.currentIndex = 3
                navRoot.pageSelected(3)
            }
        }

        NavButton {
            icon: "⚙"
            label: backend.getTextWithDefault("nav_settings", "Settings")
            selected: navRoot.currentIndex === 4
            onClicked: {
                navRoot.currentIndex = 4
                navRoot.pageSelected(4)
            }
        }

        Item { Layout.fillHeight: true }

        Label {
            Layout.fillWidth: true
            text: (backend.uiTrigger, backend.getTextWithDefault("nav_help_label", "Help & Project"))
            color: root.secondaryTextColor
            font.pixelSize: 11
            font.bold: true
            font.letterSpacing: 0.6
            leftPadding: 4
        }

        NavButton {
            icon: "❤"
            label: backend.getTextWithDefault("nav_support", "Support")
            onClicked: backend.openUrl("https://www.patreon.com/c/LordOfTurk")
        }

        NavButton {
            icon: "📖"
            label: backend.getTextWithDefault("nav_wiki", "Wiki")
            onClicked: backend.openUrl("https://github.com/Lord0fTurk/RenLocalizer/wiki")
        }

        NavButton {
            icon: "ℹ"
            label: backend.getTextWithDefault("nav_about", "About")
            selected: navRoot.currentIndex === 5
            onClicked: {
                navRoot.currentIndex = 5
                navRoot.pageSelected(5)
            }
        }
    }

    component NavButton: Rectangle {
        property string icon: ""
        property string label: ""
        property bool selected: false
        signal clicked()

        Layout.fillWidth: true
        Layout.preferredHeight: 48
        radius: 14
        color: {
            if (mouseArea.containsMouse) return root.separatorColor
            if (selected) return root.currentTheme === "light" ? Qt.alpha(Material.accent, 0.12) : root.cardBackground
            return "transparent"
        }
        border.width: selected ? 1 : 0
        border.color: Qt.alpha(Material.accent, 0.5)

        Behavior on color { ColorAnimation { duration: 150 } }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Label {
                text: icon
                font.pixelSize: 20
                font.family: root.iconFontFamily
                opacity: selected ? 1.0 : 0.78
            }

            Label {
                Layout.fillWidth: true
                text: label
                color: root.mainTextColor
                elide: Text.ElideRight
                font.bold: selected
            }
        }

        Rectangle {
            visible: selected
            width: 3
            height: parent.height - 12
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            radius: 2
            color: Material.accent
        }

        MouseArea {
            id: mouseArea
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }
}
