// LiteMain.qml — RenLocalizer Lite Ana Pencere
// Tek sayfa, navigasyon yok, sadece "Oyun Seç → Çevir" akışı.
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Window

ApplicationWindow {
    id: root
    title: liteBackend.uiTrigger, liteBackend.getTextWithDefault("app_title", "RenLocalizer") + " Lite"
    width: Math.min(900, Screen.desktopAvailableWidth * 0.85)
    height: Math.min(680, Screen.desktopAvailableHeight * 0.85)
    minimumWidth: 720
    minimumHeight: 560
    visible: false  // show() Python tarafından çağrılır

    // ── Global Theme Colors Manager ──────────────────────────────────────

    readonly property string currentTheme: liteBackend.uiTrigger, liteBackend.getCurrentTheme()

    // Material Tema Ayarları
    Material.theme: (currentTheme === "light") ? Material.Light : Material.Dark

    Material.accent: {
        if (currentTheme === "red") return "#f03e3e"
        if (currentTheme === "turquoise") return "#0ca678"
        if (currentTheme === "green") return "#37b24d"
        if (currentTheme === "neon") return "#ae3ec9"
        if (currentTheme === "light") return "#4c6ef5"
        return "#7950f2"
    }

    Material.primary: {
        if (currentTheme === "light") return "#ffffff"
        if (currentTheme === "red") return "#211222"
        if (currentTheme === "turquoise") return "#081d28"
        if (currentTheme === "green") return "#06150c"
        if (currentTheme === "neon") return "#10091e"
        return "#1a1a2e"
    }

    Material.background: {
        if (currentTheme === "light") return "#f8f9fa"
        if (currentTheme === "red") return "#170a18"
        if (currentTheme === "turquoise") return "#05131a"
        if (currentTheme === "green") return "#040d07"
        if (currentTheme === "neon") return "#090511"
        return "#121224"
    }

    color: Material.background

    // ── Renk tokenları ──────────────────────────────────────────────────
    readonly property color cardBg: {
        if (currentTheme === "light") return "#ffffff"
        if (currentTheme === "red") return "#2d1b2e"
        if (currentTheme === "turquoise") return "#0d2b3a"
        if (currentTheme === "green") return "#0a1f12"
        if (currentTheme === "neon") return "#1a0f2d"
        return "#1e1e38"
    }

    readonly property color inputBg: {
        if (currentTheme === "light") return "#f1f3f5"
        if (currentTheme === "red") return "#211222"
        if (currentTheme === "turquoise") return "#081d28"
        if (currentTheme === "green") return "#06150c"
        if (currentTheme === "neon") return "#10091e"
        return "#1a1a2e"
    }

    readonly property color borderClr: {
        if (currentTheme === "light") return "#e2e8f0"
        if (currentTheme === "red") return "#5c2134"
        if (currentTheme === "turquoise") return "#0e4b5a"
        if (currentTheme === "green") return "#0f3c21"
        if (currentTheme === "neon") return "#341a54"
        return "#2e2e4f"
    }
    readonly property color txtMain: (currentTheme === "light") ? "#212529" : "#ffffff"
    readonly property color txtSecond: (currentTheme === "light") ? "#495057" : "#aaaaaa"
    readonly property color accentClr: Material.accent
    readonly property color successClr: "#6bcb77"
    readonly property color warningClr: "#f39c12"
    readonly property color errorClr: "#ff6b6b"

    // ── State ────────────────────────────────────────────────────────────
    property bool isTranslating: false
    property string currentStage: "idle"
    property int totalLines: 0
    property int translatedLines: 0
    property real successRate: 0.0
    property string outputPath: ""

    // ── Başlangıç: son proje yolunu geri yükle ──────────────────────────
    Component.onCompleted: {
        var last = liteBackend.getLastProjectPath()
        if (last && last.length > 0) {
            projectPathField.text = last
        }

        // Hedef dili de geri yükle
        var currentLang = liteBackend.getTargetLanguage()
        var idx = targetLangCombo.indexOfValue(currentLang)
        if (idx >= 0) targetLangCombo.currentIndex = idx

        // Başlangıçta güncellemeleri denetle
        liteBackend.checkForUpdates(false)
    }

    // ── Backend Sinyalleri ───────────────────────────────────────────────
    Connections {
        target: liteBackend

        function onLogMessage(level, message) {
            appendLog(level, message)
        }

        function onProgressChanged(current, total, text) {
            if (total > 0)
                progressBar.value = current / total
            progressLabel.text = text + " (" + current + "/" + total + ")"
        }

        function onStageChanged(stage, displayName) {
            currentStage = stage
            stageLabel.text = displayName
            var stageProgress = {
                "idle": 0, "validating": 5, "unren": 15,
                "generating": 30, "parsing": 40,
                "saving": 90, "completed": 100, "error": 0
            }
            if (stage !== "translating" && stageProgress[stage] !== undefined)
                progressBar.value = stageProgress[stage] / 100
        }

        function onTranslationStarted() {
            isTranslating = true
            progressBar.value = 0
            progressLabel.text = ""
            stageLabel.text = liteBackend.getTextWithDefault("starting_translation", "Başlatılıyor...")
        }

        function onTranslationFinished(success, message) {
            isTranslating = false
            if (success) {
                stageLabel.text = liteBackend.getTextWithDefault("stage_completed", "Tamamlandı") + " ✅"
                progressBar.value = 1.0
                showToast(liteBackend.getTextWithDefault("translation_completed", "Çeviri tamamlandı!"), "success")
            } else {
                stageLabel.text = liteBackend.getTextWithDefault("stage_error", "Hata") + " ❌"
                showToast(liteBackend.getTextWithDefault("pipeline_translate_failed", "Çeviri başarısız") + ": " + message, "error")
            }
        }

        function onStatsReady(total, translated, untranslated) {
            totalLines = total
            translatedLines = translated
            successRate = total > 0 ? (translated / total) * 100 : 0
            statsCard.visible = true
            appendLog("success",
                "📊 " + liteBackend.getTextWithDefault("original_text", "Toplam") + ": " + total +
                " | " + liteBackend.getTextWithDefault("completed", "Çevrildi") + ": " + translated +
                " | " + liteBackend.getTextWithDefault("untranslated", "Kalan") + ": " + untranslated +
                " | " + liteBackend.getTextWithDefault("ratio", "Oran") + ": " + successRate.toFixed(1) + "%"
            )
        }

        function onCompletionSummary(title, message, outPath, diagPath, reviewCount) {
            outputPath = outPath
            completionDialog.summaryText = message
            completionDialog.outputPath = outPath
            completionDialog.diagPath = diagPath
            completionDialog.open()
        }

        function onWarningMessage(title, message) {
            warningDialog.titleText = title
            warningDialog.bodyText = message
            warningDialog.open()
        }

        function onUpdateAvailable(currentVersion, latestVersion, releaseUrl) {
            updateDialog.latestVersion = latestVersion
            updateDialog.releaseUrl = releaseUrl
            updateDialog.open()
        }

        function onUpdateCheckFinished(hasUpdate, message) {
            if (hasUpdate || settingsPopup.visible) {
                showToast(message, hasUpdate ? "success" : "info")
            }
        }
    }

    // ── Yardımcı JS Fonksiyonları ────────────────────────────────────────
    ListModel { id: logModel }

    function appendLog(level, message) {
        var ts = new Date().toLocaleTimeString(Qt.locale(), "HH:mm:ss")
        logModel.append({ "level": level, "message": message, "ts": ts })
        logListView.positionViewAtEnd()
    }

    function showToast(msg, type) {
        toast.message = msg
        toast.toastType = type
        toast.opacity = 1.0
        toastTimer.restart()
    }

    function logColor(level) {
        if (level === "error")   return errorClr
        if (level === "warning") return warningClr
        if (level === "success") return successClr
        if (level === "debug")   return "#888888"
        return txtMain
    }

    function logPrefix(level) {
        var trigger = liteBackend.uiTrigger;
        if (level === "error")   return "[" + liteBackend.getTextWithDefault("log_tag_error", "ERROR").replace("[", "").replace("]", "") + "] "
        if (level === "warning") return "[" + liteBackend.getTextWithDefault("log_tag_warn", "WARN").replace("[", "").replace("]", "") + "] "
        if (level === "success") return "[✓] "
        if (level === "debug")   return "[" + liteBackend.getTextWithDefault("log_tag_debug", "DEBUG").replace("[", "").replace("]", "") + "] "
        return "[" + liteBackend.getTextWithDefault("log_tag_info", "INFO").replace("[", "").replace("]", "") + "] "
    }

    // ── Dosya Diyalogları ────────────────────────────────────────────────
    FileDialog {
        id: fileDialog
        title: liteBackend.uiTrigger, liteBackend.getTextWithDefault("select_game_exe_title", "Oyun EXE Dosyasını Seç")
        nameFilters: Qt.platform.os === "windows"
            ? [liteBackend.getTextWithDefault("renpy_games_filter", "Ren'Py Oyunları") + " (*.exe)", liteBackend.getTextWithDefault("all_files_filter", "Tüm dosyalar") + " (*)"]
            : [liteBackend.getTextWithDefault("shell_scripts_filter", "Shell scriptleri") + " (*.sh)", liteBackend.getTextWithDefault("all_files_filter", "Tüm dosyalar") + " (*)"]
        onAccepted: {
            var raw = selectedFile.toString()
            liteBackend.setProjectPath(raw)
            projectPathField.text = liteBackend.urlToPath(raw)
        }
    }

    FolderDialog {
        id: folderDialog
        title: liteBackend.uiTrigger, liteBackend.getTextWithDefault("select_game_folder_title", "Oyun Klasörünü Seç")
        onAccepted: {
            var raw = selectedFolder.toString()
            liteBackend.setProjectPath(raw)
            projectPathField.text = liteBackend.urlToPath(raw)
        }
    }

    // ── Ana İçerik ───────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Başlık Çubuğu ─────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: 64
            color: "#0e0e20"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 14

                // Logo
                Rectangle {
                    width: 36; height: 36
                    radius: 8
                    color: Qt.rgba(121/255, 80/255, 242/255, 0.2)
                    border.color: accentClr
                    border.width: 1

                    Image {
                        anchors.fill: parent
                        anchors.margins: 4
                        source: liteBackend.get_asset_url("icon.png")
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        mipmap: true
                    }
                }

                ColumnLayout {
                    spacing: 0
                    Label {
                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("app_title", "RenLocalizer") + " Lite"
                        font.pixelSize: 20
                        font.bold: true
                        color: txtMain
                    }
                    Label {
                        text: liteBackend.uiTrigger, "Google Translate • " + liteBackend.getTextWithDefault("app_subtitle", "Ren'Py Çeviri Aracı")
                        font.pixelSize: 11
                        color: txtSecond
                    }
                }

                Item { Layout.fillWidth: true }

                // Ayarlar Butonu
                Button {
                    id: settingsBtn
                    width: 32; height: 32
                    background: Rectangle {
                        radius: 8
                        color: parent.hovered ? "#3d3d54" : "transparent"
                    }
                    contentItem: Label {
                        text: "⚙️"
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: settingsPopup.open()
                    ToolTip.text: "Gelişmiş Çeviri Ayarları"
                    ToolTip.visible: hovered
                    ToolTip.delay: 500
                }

                // Durum göstergesi
                Rectangle {
                    width: statusIndicator.implicitWidth + 20
                    height: 26
                    radius: 13
                    color: isTranslating
                        ? Qt.rgba(121/255, 80/255, 242/255, 0.2)
                        : Qt.rgba(107/255, 203/255, 119/255, 0.15)
                    border.color: isTranslating ? accentClr : successClr
                    border.width: 1

                    Label {
                        id: statusIndicator
                        anchors.centerIn: parent
                        text: liteBackend.uiTrigger, isTranslating ? liteBackend.getTextWithDefault("pipeline_logs.stage_translating", "⟳ Çeviriyor...") : "● " + liteBackend.getTextWithDefault("status_ready", "Hazır")
                        font.pixelSize: 11
                        color: isTranslating ? accentClr : successClr
                    }

                    SequentialAnimation on opacity {
                        running: isTranslating
                        loops: Animation.Infinite
                        NumberAnimation { to: 0.4; duration: 700 }
                        NumberAnimation { to: 1.0; duration: 700 }
                    }
                }
            }
        }

        // ── İçerik Bölgesi ────────────────────────────────────────────
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: Math.min(parent.width - 48, 900)
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 16
                anchors.topMargin: 20
                anchors.bottomMargin: 20

                Item { height: 4 }

                // ── Kart 1: Proje Seçimi ──────────────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    height: card1Col.height + 36
                    radius: 16
                    color: cardBg

                    // Sol vurgu çizgisi
                    Rectangle {
                        width: 3; height: parent.height - 20
                        x: 0; anchors.verticalCenter: parent.verticalCenter
                        radius: 2
                        color: accentClr
                    }

                    ColumnLayout {
                        id: card1Col
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 20
                        anchors.leftMargin: 24
                        spacing: 12

                        Label {
                            text: liteBackend.uiTrigger, "📁 " + liteBackend.getTextWithDefault("input_section", "Oyun Seç")
                            font.pixelSize: 15
                            font.bold: true
                            color: txtMain
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            TextField {
                                id: projectPathField
                                Layout.fillWidth: true
                                height: 44
                                placeholderText: "" // Disable native placeholder to prevent overlapping/floating text issues
                                color: txtMain
                                font.pixelSize: 13
                                leftPadding: 14
                                rightPadding: 14
                                verticalAlignment: TextInput.AlignVCenter

                                Label {
                                    text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("directory_placeholder", "Oyun EXE'si veya klasörünü seçin...")
                                    color: Qt.rgba(1, 1, 1, 0.3)
                                    font.pixelSize: 13
                                    anchors.left: parent.left
                                    anchors.leftMargin: 14
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: parent.text === "" && !parent.activeFocus
                                }

                                background: Rectangle {
                                    radius: 8
                                    color: inputBg
                                    border.color: projectPathField.activeFocus ? accentClr : borderClr
                                    border.width: 1
                                    Behavior on border.color { ColorAnimation { duration: 150 } }
                                }

                                onEditingFinished: {
                                    if (text.length > 0)
                                        liteBackend.setProjectPath(text)
                                }
                            }

                            // EXE Butonu
                            Button {
                                id: fileBrowseBtn
                                text: "📄 EXE"
                                height: 44
                                width: 80
                                onClicked: fileDialog.open()

                                contentItem: Label {
                                    text: parent.text
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: "white"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    radius: 8
                                    color: parent.down    ? Qt.darker(accentClr, 1.3)
                                         : parent.hovered ? Qt.darker(accentClr, 1.1)
                                         : accentClr
                                    Behavior on color { ColorAnimation { duration: 120 } }
                                }
                            }

                            // Klasör Butonu
                            Button {
                                id: folderBrowseBtn
                                text: liteBackend.uiTrigger, "📂 " + liteBackend.getTextWithDefault("browse_folder", "Klasör")
                                height: 44
                                width: 90
                                onClicked: folderDialog.open()

                                contentItem: Label {
                                    text: parent.text
                                    font.pixelSize: 12
                                    font.bold: true
                                    color: "white"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }
                                background: Rectangle {
                                    radius: 8
                                    color: parent.down    ? Qt.darker("#495057", 1.3)
                                         : parent.hovered ? "#6c757d"
                                         : "#495057"
                                    Behavior on color { ColorAnimation { duration: 120 } }
                                }
                            }
                        }
                    }
                }

                // ── Kart 2: Dil + Başlat ──────────────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    height: card2Col.height + 36
                    radius: 16
                    color: cardBg

                    Rectangle {
                        width: 3; height: parent.height - 20
                        x: 0; anchors.verticalCenter: parent.verticalCenter
                        radius: 2
                        color: "#0ca678"
                    }

                    ColumnLayout {
                        id: card2Col
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 20
                        anchors.leftMargin: 24
                        spacing: 14

                        Label {
                            text: liteBackend.uiTrigger, "⚙️ " + liteBackend.getTextWithDefault("settings_tab_translation", "Çeviri Ayarları")
                            font.pixelSize: 15
                            font.bold: true
                            color: txtMain
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 20

                            // Motor seçimi (dinamik)
                            ColumnLayout {
                                spacing: 6
                                Label {
                                    text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("home_summary_engine", "Çeviri Motoru")
                                    color: txtSecond
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                                ComboBox {
                                    id: engineComboBox
                                    width: 180
                                    model: [
                                        { text: "🌐 Google Translate", value: "google" },
                                        { text: "🤖 OpenAI",           value: "openai" },
                                        { text: "🤖 DeepSeek",         value: "deepseek" },
                                        { text: "💻 Local LLM",        value: "local_llm" }
                                    ]
                                    textRole: "text"
                                    valueRole: "value"
                                    Component.onCompleted: {
                                        currentIndex = indexOfValue(liteBackend.selectedEngine)
                                        if (currentIndex < 0) currentIndex = 0
                                    }
                                    onActivated: liteBackend.setSelectedEngine(currentValue)
                                    background: Rectangle {
                                        radius: 8
                                        color: Qt.rgba(1, 1, 1, 0.06)
                                        border.color: borderClr
                                    }
                                    contentItem: Label {
                                        leftPadding: 10
                                        text: engineComboBox.displayText
                                        color: txtMain
                                        font.pixelSize: 12
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }

                            // Hedef dil
                            ColumnLayout {
                                spacing: 6
                                Layout.preferredWidth: 200
                                Label {
                                    text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("target_language", "Hedef Dil")
                                    color: txtSecond
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                                ComboBox {
                                    id: targetLangCombo
                                    Layout.fillWidth: true
                                    height: 40
                                    model: liteBackend.getTargetLanguages()
                                    textRole: "name"
                                    valueRole: "code"
                                    onActivated: liteBackend.setTargetLanguage(currentValue)

                                    background: Rectangle {
                                        radius: 8
                                        color: inputBg
                                        border.color: targetLangCombo.hovered ? accentClr : borderClr
                                        border.width: 1
                                        Behavior on border.color { ColorAnimation { duration: 150 } }
                                    }
                                    contentItem: Label {
                                        text: targetLangCombo.currentText
                                        color: txtMain
                                        font.pixelSize: 12
                                        verticalAlignment: Text.AlignVCenter
                                        leftPadding: 12
                                        elide: Text.ElideRight
                                    }
                                    delegate: ItemDelegate {
                                        width: targetLangCombo.width
                                        contentItem: Label {
                                            text: modelData.name
                                            color: txtMain
                                            font.pixelSize: 12
                                            verticalAlignment: Text.AlignVCenter
                                        }
                                        background: Rectangle {
                                            color: hovered ? Qt.rgba(121/255, 80/255, 242/255, 0.2) : "transparent"
                                        }
                                    }
                                    popup: Popup {
                                        y: targetLangCombo.height
                                        width: targetLangCombo.width
                                        implicitHeight: Math.min(contentItem.implicitHeight, 260)
                                        padding: 1
                                        contentItem: ListView {
                                            clip: true
                                            implicitHeight: contentHeight
                                            model: targetLangCombo.delegateModel
                                            ScrollBar.vertical: ScrollBar {}
                                        }
                                        background: Rectangle {
                                            color: "#252540"
                                            radius: 8
                                            border.color: borderClr
                                            border.width: 1
                                        }
                                    }
                                }
                            }

                            Item { Layout.fillWidth: true }

                            // Başlat / Durdur butonu
                            Button {
                                id: startBtn
                                width: 150; height: 44
                                enabled: projectPathField.text.length > 0
                                text: {
                                    var trigger = liteBackend.uiTrigger;
                                    return isTranslating 
                                        ? "⏹  " + liteBackend.getTextWithDefault("stop", "Durdur") 
                                        : "▶  " + liteBackend.getTextWithDefault("start_translation", "Çeviriyi Başlat");
                                }

                                onClicked: {
                                    if (isTranslating) {
                                        liteBackend.stopTranslation()
                                    } else {
                                        if (projectPathField.text.length > 0)
                                            liteBackend.setProjectPath(projectPathField.text)
                                        liteBackend.startTranslation()
                                    }
                                }

                                contentItem: Label {
                                    text: parent.text
                                    font.pixelSize: 13
                                    font.bold: true
                                    color: parent.enabled ? "white" : "#888"
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                }

                                background: Rectangle {
                                    id: startBtnBg
                                    radius: 10
                                    color: !parent.enabled ? "#333344"
                                         : isTranslating
                                           ? (parent.down ? "#c0392b" : parent.hovered ? "#e74c3c" : "#c0392b")
                                           : (parent.down ? Qt.darker(accentClr, 1.3)
                                              : parent.hovered ? Qt.lighter(accentClr, 1.15)
                                              : accentClr)

                                    border.color: (parent.enabled && !isTranslating && parent.hovered) 
                                        ? Qt.lighter(accentClr, 1.4) 
                                        : "transparent"
                                    border.width: (parent.enabled && !isTranslating && parent.hovered) ? 2 : 0

                                    Behavior on color { ColorAnimation { duration: 150 } }
                                    Behavior on border.color { ColorAnimation { duration: 150 } }
                                }
                            }
                        }
                    }
                }

                // ── Kart 3: İlerleme (sadece çeviri sırasında) ────────
                Rectangle {
                    id: progressCard
                    Layout.fillWidth: true
                    height: progressCol.height + 36
                    radius: 16
                    color: cardBg
                    visible: isTranslating || currentStage === "completed" || currentStage === "error"

                    Behavior on visible { PropertyAnimation { duration: 200 } }

                    Rectangle {
                        width: 3; height: parent.height - 20
                        x: 0; anchors.verticalCenter: parent.verticalCenter
                        radius: 2
                        color: currentStage === "completed" ? successClr
                             : currentStage === "error"     ? errorClr
                             : accentClr
                        Behavior on color { ColorAnimation { duration: 300 } }
                    }

                    ColumnLayout {
                        id: progressCol
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 20
                        anchors.leftMargin: 24
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                id: stageLabel
                                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("status_ready", "Hazır")
                                font.pixelSize: 14
                                font.bold: true
                                color: txtMain
                            }
                            Item { Layout.fillWidth: true }
                            Label {
                                id: progressLabel
                                text: ""
                                font.pixelSize: 12
                                color: txtSecond
                            }
                        }

                        ProgressBar {
                            id: progressBar
                            Layout.fillWidth: true
                            value: 0; from: 0; to: 1

                            background: Rectangle {
                                radius: 5
                                color: inputBg
                                height: 8
                            }
                            contentItem: Item {
                                Rectangle {
                                    width: progressBar.visualPosition * parent.width
                                    height: 8; radius: 5
                                    color: currentStage === "completed" ? successClr : accentClr
                                    Behavior on width { NumberAnimation { duration: 200 } }
                                    Behavior on color { ColorAnimation { duration: 300 } }
                                }
                            }
                        }
                    }
                }

                // ── Kart 4: İstatistikler ─────────────────────────────
                Rectangle {
                    id: statsCard
                    Layout.fillWidth: true
                    height: 80
                    radius: 16
                    color: cardBg
                    visible: false

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 40

                        ColumnLayout {
                            spacing: 2
                            Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("original_text", "Toplam Satır"); color: txtSecond; font.pixelSize: 11 }
                            Label { text: totalLines; color: txtMain; font.pixelSize: 22; font.bold: true }
                        }
                        Rectangle { width: 1; height: 40; color: borderClr }
                        ColumnLayout {
                            spacing: 2
                            Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("completed", "Çevrildi"); color: txtSecond; font.pixelSize: 11 }
                            Label { text: translatedLines; color: successClr; font.pixelSize: 22; font.bold: true }
                        }
                        Rectangle { width: 1; height: 40; color: borderClr }
                        ColumnLayout {
                            spacing: 2
                            Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("success_rate", "Başarı Oranı"); color: txtSecond; font.pixelSize: 11 }
                            Label {
                                text: successRate.toFixed(1) + "%"
                                color: accentClr; font.pixelSize: 22; font.bold: true
                            }
                        }
                        Item { Layout.fillWidth: true }
                        Button {
                            text: liteBackend.uiTrigger, "📂 " + liteBackend.getTextWithDefault("open_directory", "Çıktıyı Aç")
                            visible: outputPath.length > 0
                            height: 36
                            onClicked: liteBackend.openLocalPath(outputPath)
                            background: Rectangle {
                                radius: 8
                                color: parent.hovered ? Qt.darker("#1971c2", 1.1) : "#1971c2"
                                Behavior on color { ColorAnimation { duration: 120 } }
                            }
                            contentItem: Label {
                                text: parent.text
                                color: "white"; font.pixelSize: 12
                                horizontalAlignment: Text.AlignHCenter
                            }
                        }
                    }
                }

                // ── Kart 5: Log Paneli ────────────────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    height: 240
                    radius: 16
                    color: inputBg
                    border.color: borderClr
                    border.width: 1
                    clip: true

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                text: liteBackend.uiTrigger, "📋 " + liteBackend.getTextWithDefault("log", "İşlem Günlüğü")
                                font.pixelSize: 13
                                font.bold: true
                                color: txtMain
                            }
                            Item { Layout.fillWidth: true }
                            Label {
                                text: liteBackend.uiTrigger, logModel.count + " " + liteBackend.getTextWithDefault("lines", "satır")
                                font.pixelSize: 11
                                color: txtSecond
                            }
                            // Log kopyala butonu
                            Button {
                                text: "📋"
                                width: 28; height: 28
                                onClicked: {
                                    var fullLog = ""
                                    for (var i = 0; i < logModel.count; i++) {
                                        var item = logModel.get(i)
                                        fullLog += item.ts + " " + logPrefix(item.level) + item.message + "\n"
                                    }
                                    liteBackend.copyToClipboard(fullLog)
                                    showToast(liteBackend.getTextWithDefault("log_copy_success", "Log copied to clipboard."), "success")
                                }
                                ToolTip.text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("copy_log", "Günlüğü kopyala")
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                background: Rectangle {
                                    radius: 6
                                    color: parent.hovered ? "#3d3d54" : "transparent"
                                }
                                contentItem: Label {
                                    text: parent.text
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    font.pixelSize: 13
                                }
                            }

                            // Log temizle butonu
                            Button {
                                text: "🗑"
                                width: 28; height: 28
                                onClicked: logModel.clear()
                                ToolTip.text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("clear_log", "Günlüğü temizle")
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                background: Rectangle {
                                    radius: 6
                                    color: parent.hovered ? "#3d3d54" : "transparent"
                                }
                                contentItem: Label {
                                    text: parent.text
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    font.pixelSize: 13
                                }
                            }
                        }

                        ListView {
                            id: logListView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            model: logModel
                            clip: true
                            spacing: 1
                            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                            delegate: RowLayout {
                                width: logListView.width
                                spacing: 6

                                Label {
                                    text: model.ts
                                    font.pixelSize: 10
                                    font.family: "Consolas, monospace"
                                    color: "#555577"
                                    Layout.preferredWidth: 60
                                }
                                Label {
                                    text: logPrefix(model.level) + model.message
                                    font.pixelSize: 11
                                    font.family: "Consolas, monospace"
                                    color: logColor(model.level)
                                    Layout.fillWidth: true
                                    wrapMode: Text.Wrap
                                }
                            }
                        }
                    }
                }

                // ── İpucu kutusu ─────────────────────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: tipLayout.implicitHeight + 24
                    radius: 10
                    color: Qt.rgba(243/255, 156/255, 18/255, 0.1)
                    border.color: Qt.rgba(243/255, 156/255, 18/255, 0.4)
                    border.width: 1

                    RowLayout {
                        id: tipLayout
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 10

                        Label {
                            text: "💡"
                            font.pixelSize: 16
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Label {
                            Layout.fillWidth: true
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_tip_desc", "Lite sürüm arayüzü sadeleştirilmiş hızlı çeviri modudur. Gelişmiş ince ayarlar, toplu sözlük yönetimi, font araçları ve özel çıkarma seçenekleri için tam RenLocalizer sürümünü kullanın.")
                            color: "#f39c12"
                            font.pixelSize: 12
                            wrapMode: Text.Wrap
                            Layout.alignment: Qt.AlignVCenter
                        }
                    }
                }

                // ── Wiki Kılavuzu Yönlendirme Butonu ─────────────────────────
                Button {
                    Layout.fillWidth: true
                    height: 38
                    
                    contentItem: RowLayout {
                        anchors.centerIn: parent
                        spacing: 8
                        Label {
                            text: "📖"
                            font.pixelSize: 14
                        }
                        Label {
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_guide_btn", "Open RenLocalizer Lite Wiki Guide")
                            font.pixelSize: 12
                            font.bold: true
                            color: "white"
                        }
                    }

                    background: Rectangle {
                        radius: 8
                        color: parent.down ? Qt.darker("#2b8a3e", 1.2) : parent.hovered ? "#2b8a3e" : "#2f9e44"
                        border.color: parent.hovered ? "#40c057" : "transparent"
                        border.width: 1
                        Behavior on color { ColorAnimation { duration: 120 } }
                    }

                    onClicked: {
                        Qt.openUrlExternally("https://github.com/Lord0fTurk/RenLocalizer/wiki/LITE-RELEASE-GUIDE")
                    }
                }

                Item { height: 8 }
            }
        }

        // ── Alt Durum Çubuğu ──────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            height: 24
            color: "#0a0a18"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 16

                Label {
                    text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("app_title", "RenLocalizer") + " Lite v" + liteBackend.version
                    font.pixelSize: 10
                    color: "#555577"
                }
                Label {
                    text: "Google Translate"
                    font.pixelSize: 10
                    color: "#555577"
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: liteBackend.uiTrigger, isTranslating ? liteBackend.getTextWithDefault("pipeline_logs.stage_translating", "⟳ Çeviriyor...") : "● " + liteBackend.getTextWithDefault("status_ready", "Hazır")
                    font.pixelSize: 10
                    color: isTranslating ? accentClr : successClr
                }
            }
        }
    }

    // ── Toast Bildirimi ──────────────────────────────────────────────────
    Rectangle {
        id: toast
        property string message: ""
        property string toastType: "info"

        z: 9999
        visible: opacity > 0
        opacity: 0

        anchors.bottom: parent.bottom
        anchors.bottomMargin: 36
        anchors.horizontalCenter: parent.horizontalCenter

        width: Math.min(toastContent.implicitWidth + 48, root.width - 60)
        height: Math.max(48, toastContent.implicitHeight + 20)
        radius: 10

        color: toastType === "error"   ? "#c92a2a"
             : toastType === "success" ? "#2b8a3e"
             : toastType === "warning" ? "#e67700"
             : "#495057"

        border.color: "white"
        border.width: 1

        RowLayout {
            id: toastContent
            anchors.fill: parent
            anchors.margins: 12
            spacing: 10

            Label {
                text: toast.toastType === "success" ? "✅"
                    : toast.toastType === "error"   ? "❌"
                    : toast.toastType === "warning"  ? "⚠️"
                    : "ℹ️"
                font.pixelSize: 16
            }

            Label {
                text: toast.message
                color: "white"
                font.bold: true
                font.pixelSize: 13
                Layout.fillWidth: true
                wrapMode: Text.Wrap
                verticalAlignment: Text.AlignVCenter
            }
        }

        Behavior on opacity { NumberAnimation { duration: 400 } }

        Timer {
            id: toastTimer
            interval: 6000
            onTriggered: toast.opacity = 0
        }

        MouseArea {
            anchors.fill: parent
            onClicked: toast.opacity = 0
        }
    }

    // ── Uyarı Dialogu ────────────────────────────────────────────────────
    Dialog {
        id: warningDialog
        property string titleText: {
            var trigger = liteBackend.uiTrigger;
            return liteBackend.getTextWithDefault("warning", "Uyarı");
        }
        property string bodyText: ""

        anchors.centerIn: parent
        width: Math.min(400, root.width * 0.85)
        modal: true
        title: "⚠️ " + titleText

        background: Rectangle {
            color: "#1e1e38"
            radius: 14
            border.color: warningClr
            border.width: 1
        }

        contentItem: Label {
            text: warningDialog.bodyText
            color: txtMain
            wrapMode: Text.Wrap
            font.pixelSize: 13
            horizontalAlignment: Text.AlignHCenter
            padding: 20
        }

        footer: DialogButtonBox {
            background: Rectangle { color: "transparent" }
            Button {
                text: {
                    var trigger = liteBackend.uiTrigger;
                    return liteBackend.getTextWithDefault("btn_ok", "Tamam");
                }
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                background: Rectangle { radius: 8; color: accentClr }
                contentItem: Label {
                    text: parent.text; color: "white"
                    horizontalAlignment: Text.AlignHCenter
                }
                onClicked: warningDialog.close()
            }
            alignment: Qt.AlignHCenter
            padding: 10
        }
    }

    // ── Tamamlanma Dialogu ───────────────────────────────────────────────
    Dialog {
        id: completionDialog
        property string summaryText: ""
        property string outputPath: ""
        property string diagPath: ""

        anchors.centerIn: parent
        width: Math.min(440, root.width * 0.85)
        modal: true
        title: {
            var trigger = liteBackend.uiTrigger;
            return "✅ " + liteBackend.getTextWithDefault("translation_complete_title", "Çeviri Tamamlandı");
        }

        background: Rectangle {
            color: "#1e1e38"
            radius: 14
            border.color: successClr
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: 12

            Label {
                text: completionDialog.summaryText
                color: txtMain
                wrapMode: Text.Wrap
                font.pixelSize: 13
                Layout.fillWidth: true
                Layout.margins: 20
                horizontalAlignment: Text.AlignHCenter
            }
        }

        footer: DialogButtonBox {
            background: Rectangle { color: "transparent" }

            Button {
                visible: completionDialog.outputPath.length > 0
                text: {
                    var trigger = liteBackend.uiTrigger;
                    return "📂 " + liteBackend.getTextWithDefault("translation_complete_open_output", "Çıktıyı Aç");
                }
                DialogButtonBox.buttonRole: DialogButtonBox.ActionRole
                background: Rectangle { radius: 8; color: "#1971c2" }
                contentItem: Label {
                    text: parent.text; color: "white"
                    horizontalAlignment: Text.AlignHCenter
                }
                onClicked: liteBackend.openLocalPath(completionDialog.outputPath)
            }

            Button {
                text: {
                    var trigger = liteBackend.uiTrigger;
                    return liteBackend.getTextWithDefault("btn_close", "Kapat");
                }
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                background: Rectangle { radius: 8; color: accentClr }
                contentItem: Label {
                    text: parent.text; color: "white"
                    horizontalAlignment: Text.AlignHCenter
                }
                onClicked: completionDialog.close()
            }
            alignment: Qt.AlignHCenter
            padding: 10
        }
    }

    // ── Gelişmiş Ayarlar Diyalogu ─────────────────────────────────────────
    Dialog {
        id: settingsPopup
        title: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_settings_title", "⚙️ Advanced Translation Settings")
        anchors.centerIn: parent
        width: Math.min(460, root.width * 0.9)
        height: Math.min(600, root.height * 0.9)
        modal: true

        background: Rectangle {
            color: "#1e1e38"
            radius: 14
            border.color: borderClr
            border.width: 1
        }

        onOpened: {
            threadsSlider.value = liteBackend.maxConcurrentThreads
            delaySlider.value = liteBackend.requestDelay
            batchSlider.value = liteBackend.maxBatchSize
            multiSwitch.checked = liteBackend.useMultiEndpoint
            lingvaSwitch.checked = liteBackend.enableLingvaFallback
            aggressiveSwitch.checked = liteBackend.aggressiveRetry
            cacheSwitch.checked = liteBackend.useCache
            updateStartupSwitch.checked = liteBackend.checkForUpdatesOnStartup
            rpycSwitch.checked = liteBackend.enableRpycReader
            deepScanSwitch.checked = liteBackend.enableDeepScan

            // Advanced AI Settings
            aiTempSlider.value = liteBackend.aiTemperature
            aiTimeoutSlider.value = liteBackend.aiTimeout
            aiMaxTokensSlider.value = liteBackend.aiMaxTokens
            aiBatchSlider.value = liteBackend.aiBatchSize
            aiRetrySlider.value = liteBackend.aiRetryCount
            aiConcurrencySlider.value = liteBackend.aiConcurrency
            aiDelaySlider.value = liteBackend.aiRequestDelay
            aiSysPromptField.text = liteBackend.aiCustomSystemPrompt

            // UI Language
            var curLang = liteBackend.getCurrentUILanguage()
            var langIdx = uiLanguageCombo.indexOfValue(curLang)
            if (langIdx >= 0) uiLanguageCombo.currentIndex = langIdx

            // UI Theme
            var curTheme = liteBackend.getCurrentTheme()
            var themeIdx = uiThemeCombo.indexOfValue(curTheme)
            if (themeIdx >= 0) uiThemeCombo.currentIndex = themeIdx
        }

        contentItem: ScrollView {
            id: settingsScroll
            clip: true
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: settingsScroll.availableWidth - 16
                spacing: 16
                Layout.leftMargin: 8
                Layout.rightMargin: 8
                Layout.topMargin: 10
                Layout.bottomMargin: 10

                Label {
                    text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_ui_settings", "UI Settings")
                    font.pixelSize: 14
                    font.bold: true
                    color: accentClr
                }

                // UI Language
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Label {
                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ui_language_label", "UI Language:")
                        color: txtMain
                        font.bold: true
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                    ComboBox {
                        id: uiLanguageCombo
                        Layout.preferredWidth: 180
                        model: liteBackend.getAvailableUILanguages()
                        textRole: "name"
                        valueRole: "code"
                    }
                }

                // UI Theme
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Label {
                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("theme_label", "Theme:")
                        color: txtMain
                        font.bold: true
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                    ComboBox {
                        id: uiThemeCombo
                        Layout.preferredWidth: 180
                        model: liteBackend.getAvailableThemes()
                        textRole: "name"
                        valueRole: "code"
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: borderClr }

                // Update Settings
                Label {
                    text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("update_check_title", "Update Check")
                    font.pixelSize: 14
                    font.bold: true
                    color: accentClr
                }

                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        Label {
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("check_updates", "Check for Updates")
                            color: txtMain
                            font.bold: true
                            font.pixelSize: 12
                        }
                        Label {
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("check_updates_desc", "Check for updates on startup")
                            color: txtSecond
                            font.pixelSize: 10
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }
                    Switch {
                        id: updateStartupSwitch
                    }
                }

                Button {
                    Layout.fillWidth: true
                    text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("check_updates_now_button", "Check")
                    height: 36
                    background: Rectangle {
                        radius: 8
                        color: parent.hovered ? Qt.darker(accentClr, 1.1) : accentClr
                    }
                    contentItem: Label {
                        text: parent.text
                        color: "white"
                        font.bold: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: {
                        liteBackend.checkForUpdates(true)
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: borderClr }

                Label {
                    text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("settings_engines_title", "Translation Engines & APIs")
                    font.pixelSize: 14
                    font.bold: true
                    color: accentClr
                }

                // 1. Threads
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_concurrency_label", "Concurrent Request Limit"); color: txtMain; font.bold: true; font.pixelSize: 12 }
                        Item { Layout.fillWidth: true }
                        Label { text: Math.round(threadsSlider.value); color: accentClr; font.bold: true; font.pixelSize: 12 }
                    }
                    Slider {
                        id: threadsSlider
                        Layout.fillWidth: true
                        from: 1; to: 32; stepSize: 1
                        live: true
                    }
                    Label {
                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_concurrency_desc", "Number of parallel requests to send. Higher values increase rate limit risks.")
                        color: txtSecond; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true
                    }
                }

                // 2. Request Delay
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_delay_label", "Request Delay (Seconds)"); color: txtMain; font.bold: true; font.pixelSize: 12 }
                        Item { Layout.fillWidth: true }
                        Label { text: delaySlider.value.toFixed(2) + "s"; color: accentClr; font.bold: true; font.pixelSize: 12 }
                    }
                    Slider {
                        id: delaySlider
                        Layout.fillWidth: true
                        from: 0.0; to: 3.0; stepSize: 0.05
                        live: true
                    }
                    Label {
                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_delay_desc", "Delay between requests. Increase this to avoid Google blocks.")
                        color: txtSecond; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true
                    }
                }

                // 3. Batch Size
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_batch_label", "Batch Size (Lines)"); color: txtMain; font.bold: true; font.pixelSize: 12 }
                        Item { Layout.fillWidth: true }
                        Label { text: Math.round(batchSlider.value); color: accentClr; font.bold: true; font.pixelSize: 12 }
                    }
                    Slider {
                        id: batchSlider
                        Layout.fillWidth: true
                        from: 10; to: 500; stepSize: 10
                        live: true
                    }
                    Label {
                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_batch_desc", "Number of lines packed in a single request. Lower values reduce rate limit risks.")
                        color: txtSecond; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: borderClr }

                // 4. Multi-Endpoint
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("use_multi_endpoint_label", "Use Multi-Endpoint"); color: txtMain; font.bold: true; font.pixelSize: 12 }
                        Label {
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_multi_endpoint_desc", "Distribute requests to multiple Google mirror servers to make blocking harder.")
                            color: txtSecond; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true
                        }
                    }
                    Switch {
                        id: multiSwitch
                    }
                }

                // 5. Lingva Fallback
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("enable_lingva_fallback_label", "Lingva Fallback"); color: txtMain; font.bold: true; font.pixelSize: 12 }
                        Label {
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_lingva_desc", "Redirect to free Lingva mirrors when main servers return 429.")
                            color: txtSecond; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true
                        }
                    }
                    Switch {
                        id: lingvaSwitch
                    }
                }

                // 6. Aggressive Retry
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("aggressive_retry", "Aggressive Translation"); color: txtMain; font.bold: true; font.pixelSize: 12 }
                        Label {
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_aggressive_desc", "Retry lines that return unchanged on alternative servers (slower).")
                            color: txtSecond; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true
                        }
                    }
                    Switch {
                        id: aggressiveSwitch
                    }
                }

                // 6.1 RPYC Reader
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("enable_rpyc_reader_label", "RPYC Reader (Experimental)"); color: txtMain; font.bold: true; font.pixelSize: 12 }
                        Label {
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("rpyc_reader_desc", "Reads compiled .rpyc files directly via AST extraction; no decompilation needed.")
                            color: txtSecond; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true
                        }
                    }
                    Switch {
                        id: rpycSwitch
                    }
                }

                // 6.2 Deep Scan
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        spacing: 2
                        Layout.fillWidth: true
                        Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("deep_scan", "Deep Scan"); color: txtMain; font.bold: true; font.pixelSize: 12 }
                        Label {
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("deep_scan_desc", "Analyze RPYC files with AST (slower).")
                            color: txtSecond; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true
                        }
                    }
                    Switch {
                        id: deepScanSwitch
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: borderClr }

                // 7. Clear Cache Button
                ColumnLayout {
                    id: cacheSectionLayout
                    Layout.fillWidth: true
                    spacing: 6
                    Label {
                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_cache_title", "Translation Cache (TM) Management")
                        color: txtMain
                        font.bold: true
                        font.pixelSize: 12
                    }
                    // 7.1 Cache Usage Switch
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: 2
                            Layout.fillWidth: true
                            Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_use_cache_label", "Use Translation Cache (TM)"); color: txtMain; font.bold: true; font.pixelSize: 12 }
                            Label {
                                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_use_cache_desc", "Read already translated lines from cache to complete translation instantly.")
                                color: txtSecond; font.pixelSize: 10; wrapMode: Text.Wrap; Layout.fillWidth: true
                            }
                        }
                        Switch {
                            id: cacheSwitch
                        }
                    }
                    Label {
                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_clear_cache_desc", "Purge cached translations for the selected project to start translation from scratch.")
                        color: txtSecond
                        font.pixelSize: 10
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    Button {
                        id: clearCacheBtn
                        Layout.fillWidth: true
                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_clear_cache_btn", "🧹 Clear Translation Cache")
                        background: Rectangle {
                            radius: 8
                            color: parent.hovered ? "#bd2130" : "#dc3545"
                        }
                        contentItem: Label {
                            text: parent.text
                            color: "white"
                            font.bold: true
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        onClicked: {
                            if (liteBackend.clearTranslationCache()) {
                                showToast(liteBackend.getTextWithDefault("log_cache_cleared", "Translation memory cleared."), "success")
                            } else {
                                showToast(liteBackend.getTextWithDefault("log_cache_clear_error", "Error clearing cache: no project selected."), "error")
                            }
                        }
                    }
                }

                // 7. AI Motor Ayarları (Modernized Card Wrapper inside ScrollView)
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: aiGroup.implicitHeight + 24
                    color: Qt.rgba(1, 1, 1, 0.15)
                    border.color: Qt.rgba(255, 255, 255, 0.08)
                    border.width: 1
                    radius: 10

                    ColumnLayout {
                        id: aiGroup
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 12

                        Label {
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_ai_settings_title", "🤖 AI Motor Settings")
                            color: accentClr
                            font.pixelSize: 13
                            font.bold: true
                        }

                        // OpenAI / DeepSeek için API Key
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: engineComboBox.currentValue === "openai" || engineComboBox.currentValue === "deepseek"

                            Label {
                                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("openai_api_key_label", "OpenAI / DeepSeek API Key:")
                                color: txtMain
                                font.pixelSize: 11
                                font.bold: true
                            }
                            TextField {
                                id: openaiKeyField
                                Layout.fillWidth: true
                                text: liteBackend.openaiApiKey
                                placeholderText: "sk-..."
                                echoMode: TextInput.Password
                                color: txtMain
                                background: Rectangle {
                                    radius: 8
                                    color: Qt.rgba(1, 1, 1, 0.05)
                                    border.color: parent.activeFocus ? accentClr : borderClr
                                    border.width: parent.activeFocus ? 2 : 1
                                }
                            }

                            Label {
                                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_model_label", "Model:")
                                color: txtMain
                                font.pixelSize: 11
                                font.bold: true
                            }
                            TextField {
                                id: openaiModelField
                                Layout.fillWidth: true
                                text: liteBackend.openaiModel
                                placeholderText: engineComboBox.currentValue === "deepseek" ? "deepseek-v4-flash" : "gpt-4o-mini"
                                color: txtMain
                                background: Rectangle {
                                    radius: 8
                                    color: Qt.rgba(1, 1, 1, 0.05)
                                    border.color: parent.activeFocus ? accentClr : borderClr
                                    border.width: parent.activeFocus ? 2 : 1
                                }
                            }

                            Label {
                                text: engineComboBox.currentValue === "deepseek" ? 
                                    (liteBackend.uiTrigger, liteBackend.getTextWithDefault("deepseek_url_label", "DeepSeek API URL:")) : 
                                    (liteBackend.uiTrigger, liteBackend.getTextWithDefault("openai_base_url_label", "Base URL (Optional, empty = OpenAI):"))
                                color: txtMain
                                font.pixelSize: 11
                                font.bold: true
                            }
                            TextField {
                                id: openaiBaseUrlField
                                Layout.fillWidth: true
                                text: engineComboBox.currentValue === "deepseek" ? "https://api.deepseek.com/v1" : liteBackend.openaiBaseUrl
                                placeholderText: "https://api.openai.com/v1"
                                color: txtMain
                                background: Rectangle {
                                    radius: 8
                                    color: Qt.rgba(1, 1, 1, 0.05)
                                    border.color: parent.activeFocus ? accentClr : borderClr
                                    border.width: parent.activeFocus ? 2 : 1
                                }
                            }
                        }

                        // Local LLM ayarları
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6
                            visible: engineComboBox.currentValue === "local_llm"

                            Label {
                                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("local_llm_url_label", "Ollama / LM Studio URL:")
                                color: txtMain
                                font.pixelSize: 11
                                font.bold: true
                            }
                            TextField {
                                id: localLlmUrlField
                                Layout.fillWidth: true
                                text: liteBackend.localLlmUrl
                                placeholderText: "http://localhost:11434/v1"
                                color: txtMain
                                background: Rectangle {
                                    radius: 8
                                    color: Qt.rgba(1, 1, 1, 0.05)
                                    border.color: parent.activeFocus ? accentClr : borderClr
                                    border.width: parent.activeFocus ? 2 : 1
                                }
                            }

                            Label {
                                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("local_llm_model_label", "Model Name:")
                                color: txtMain
                                font.pixelSize: 11
                                font.bold: true
                            }
                            TextField {
                                id: localLlmModelField
                                Layout.fillWidth: true
                                text: liteBackend.localLlmModel
                                placeholderText: "qwen2.5-coder:7b-instruct, dolphin-2.9-llama3-8b..."
                                color: txtMain
                                background: Rectangle {
                                    radius: 8
                                    color: Qt.rgba(1, 1, 1, 0.05)
                                    border.color: parent.activeFocus ? accentClr : borderClr
                                    border.width: parent.activeFocus ? 2 : 1
                                }
                            }

                        }

                        // Gelişmiş AI Ayarları (AI motorları seçiliyken görünür)
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            visible: engineComboBox.currentValue !== "google"

                            // Ayırıcı çizgi
                            Rectangle {
                                Layout.fillWidth: true
                                height: 1
                                color: borderClr
                                opacity: 0.3
                            }

                            Label {
                                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("advanced_settings", "Gelişmiş Ayarlar")
                                color: accentClr
                                font.pixelSize: 12
                                font.bold: true
                            }

                            // 1. Temperature Slider
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_creativity_label", "Creativity (Temperature):"); color: txtMain; font.bold: true; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: aiTempSlider.value.toFixed(2); color: accentClr; font.bold: true; font.pixelSize: 11 }
                                }
                                Slider {
                                    id: aiTempSlider
                                    Layout.fillWidth: true
                                    from: 0.0; to: 2.0; stepSize: 0.05
                                    live: true
                                }
                            }

                            // 2. AI Batch Size Slider
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_batch_important_label", "AI Batch Size:"); color: txtMain; font.bold: true; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(aiBatchSlider.value); color: accentClr; font.bold: true; font.pixelSize: 11 }
                                }
                                Slider {
                                    id: aiBatchSlider
                                    Layout.fillWidth: true
                                    from: 1; to: 200; stepSize: 5
                                    live: true
                                }
                            }

                            // 3. AI Concurrency Slider
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_parallel_label", "AI Parallel Requests:"); color: txtMain; font.bold: true; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(aiConcurrencySlider.value); color: accentClr; font.bold: true; font.pixelSize: 11 }
                                }
                                Slider {
                                    id: aiConcurrencySlider
                                    Layout.fillWidth: true
                                    from: 1; to: 20; stepSize: 1
                                    live: true
                                }
                            }

                            // 4. Request Delay Slider
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_request_delay_label_sec", "AI Request Delay (Sec):"); color: txtMain; font.bold: true; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: aiDelaySlider.value.toFixed(2) + "s"; color: accentClr; font.bold: true; font.pixelSize: 11 }
                                }
                                Slider {
                                    id: aiDelaySlider
                                    Layout.fillWidth: true
                                    from: 0.0; to: 10.0; stepSize: 0.1
                                    live: true
                                }
                            }

                            // 5. Max Output Tokens
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_tokens_short", "Max Tokens:") + " (Output)"; color: txtMain; font.bold: true; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(aiMaxTokensSlider.value); color: accentClr; font.bold: true; font.pixelSize: 11 }
                                }
                                Slider {
                                    id: aiMaxTokensSlider
                                    Layout.fillWidth: true
                                    from: 256; to: 8192; stepSize: 256
                                    live: true
                                }
                            }

                            // 6. Timeout
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_timeout_short", "Timeout (Seconds):"); color: txtMain; font.bold: true; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(aiTimeoutSlider.value) + "s"; color: accentClr; font.bold: true; font.pixelSize: 11 }
                                }
                                Slider {
                                    id: aiTimeoutSlider
                                    Layout.fillWidth: true
                                    from: 10; to: 600; stepSize: 10
                                    live: true
                                }
                            }

                            // 7. Retry Count
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                RowLayout {
                                    Layout.fillWidth: true
                                    Label { text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_retry_short", "Retry Count:"); color: txtMain; font.bold: true; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(aiRetrySlider.value); color: accentClr; font.bold: true; font.pixelSize: 11 }
                                }
                                Slider {
                                    id: aiRetrySlider
                                    Layout.fillWidth: true
                                    from: 0; to: 10; stepSize: 1
                                    live: true
                                }
                            }

                            // 8. Custom System Prompt
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Label {
                                    text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_custom_system_prompt_label", "Custom System Prompt (Optional):")
                                    color: txtMain
                                    font.pixelSize: 11
                                    font.bold: true
                                }
                                TextField {
                                    id: aiSysPromptField
                                    Layout.fillWidth: true
                                    placeholderText: "Translate using a formal register..."
                                    color: txtMain
                                    background: Rectangle {
                                        radius: 8
                                        color: Qt.rgba(1, 1, 1, 0.05)
                                        border.color: parent.activeFocus ? accentClr : borderClr
                                        border.width: parent.activeFocus ? 2 : 1
                                    }
                                }
                            }

                            // Uncensored Model Tooltip Warning
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: warningText.implicitHeight + 16
                                color: Qt.rgba(240/255, 173/255, 78/255, 0.08)
                                border.color: Qt.rgba(240/255, 173/255, 78/255, 0.3)
                                border.width: 1
                                radius: 8
                                Layout.topMargin: 4
                                Layout.bottomMargin: 4

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 8
                                    spacing: 8
                                    Label {
                                        text: "💡"
                                        font.pixelSize: 14
                                    }
                                    Label {
                                        id: warningText
                                        text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("ai_uncensored_model_tooltip", "To prevent AI model refusals on romance, violence, or adult visual novel content, it is highly recommended to use Dolphin, Abliterated, or Uncensored variants.")
                                        color: "#f0ad4e"
                                        font.pixelSize: 10
                                        wrapMode: Text.Wrap
                                        Layout.fillWidth: true
                                    }
                                }
                            }
                        }

                        // Google seçiliyken bilgilendirme
                        Label {
                            visible: engineComboBox.currentValue === "google"
                            text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("google_no_key_desc", "Google Translate selected — no API key required.")
                            color: txtSecond
                            font.pixelSize: 11
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }

        footer: DialogButtonBox {
            background: Rectangle { color: "transparent" }

            Button {
                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_save_btn", "💾 Save Settings")
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                background: Rectangle { radius: 8; color: accentClr }
                contentItem: Label {
                    text: parent.text; color: "white"; font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }
                onClicked: {
                    liteBackend.maxConcurrentThreads = Math.round(threadsSlider.value)
                    liteBackend.requestDelay = delaySlider.value
                    liteBackend.maxBatchSize = Math.round(batchSlider.value)
                    liteBackend.useMultiEndpoint = multiSwitch.checked
                    liteBackend.enableLingvaFallback = lingvaSwitch.checked
                    liteBackend.aggressiveRetry = aggressiveSwitch.checked
                    liteBackend.useCache = cacheSwitch.checked
                    liteBackend.checkForUpdatesOnStartup = updateStartupSwitch.checked
                    liteBackend.enableRpycReader = rpycSwitch.checked
                    liteBackend.enableDeepScan = deepScanSwitch.checked

                    // AI engine settings
                    var eng = engineComboBox.currentValue
                    liteBackend.setSelectedEngine(eng)
                    if (eng === "openai" || eng === "deepseek") {
                        liteBackend.openaiApiKey  = openaiKeyField.text
                        liteBackend.openaiModel   = openaiModelField.text
                        liteBackend.openaiBaseUrl = openaiBaseUrlField.text
                    } else if (eng === "local_llm") {
                        liteBackend.localLlmUrl   = localLlmUrlField.text
                        liteBackend.localLlmModel = localLlmModelField.text
                    }

                    // Advanced AI settings
                    liteBackend.aiTemperature = aiTempSlider.value
                    liteBackend.aiTimeout = Math.round(aiTimeoutSlider.value)
                    liteBackend.aiMaxTokens = Math.round(aiMaxTokensSlider.value)
                    liteBackend.aiBatchSize = Math.round(aiBatchSlider.value)
                    liteBackend.aiRetryCount = Math.round(aiRetrySlider.value)
                    liteBackend.aiConcurrency = Math.round(aiConcurrencySlider.value)
                    liteBackend.aiRequestDelay = aiDelaySlider.value
                    liteBackend.aiCustomSystemPrompt = aiSysPromptField.text

                    // UI settings
                    liteBackend.setUILanguage(uiLanguageCombo.currentValue)
                    liteBackend.setTheme(uiThemeCombo.currentValue)

                    liteBackend.saveSettings()
                    settingsPopup.close()
                }
            }

            Button {
                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("lite_close_btn", "Close")
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                background: Rectangle { radius: 8; color: "#495057" }
                contentItem: Label {
                    text: parent.text; color: "white"
                    horizontalAlignment: Text.AlignHCenter
                }
                onClicked: settingsPopup.close()
            }

            alignment: Qt.AlignHCenter
            padding: 12
        }
    }

    // ── Güncelleme Dialogu ────────────────────────────────────────────────
    Dialog {
        id: updateDialog
        property string latestVersion: ""
        property string releaseUrl: ""

        anchors.centerIn: parent
        width: Math.min(420, root.width * 0.85)
        modal: true
        title: "🔔 " + (liteBackend.uiTrigger, liteBackend.getTextWithDefault("update_available_title", "Update Available"))

        background: Rectangle {
            color: "#1e1e38"
            radius: 14
            border.color: accentClr
            border.width: 1
        }

        contentItem: ColumnLayout {
            spacing: 12
            Label {
                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("update_available_message", "A new version is available: {latest} (current: {current}).\nOpen the releases page?").replace("{latest}", updateDialog.latestVersion).replace("{current}", liteBackend.version)
                color: txtMain
                wrapMode: Text.Wrap
                font.pixelSize: 13
                Layout.fillWidth: true
                Layout.margins: 20
                horizontalAlignment: Text.AlignHCenter
            }
        }

        footer: DialogButtonBox {
            background: Rectangle { color: "transparent" }

            Button {
                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("update_open_release", "Open Releases Page")
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                background: Rectangle { radius: 8; color: accentClr }
                contentItem: Label {
                    text: parent.text; color: "white"; font.bold: true
                    horizontalAlignment: Text.AlignHCenter
                }
                onClicked: {
                    Qt.openUrlExternally(updateDialog.releaseUrl)
                    updateDialog.close()
                }
            }

            Button {
                text: liteBackend.uiTrigger, liteBackend.getTextWithDefault("update_later", "Later")
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                background: Rectangle { radius: 8; color: "#495057" }
                contentItem: Label {
                    text: parent.text; color: "white"
                    horizontalAlignment: Text.AlignHCenter
                }
                onClicked: updateDialog.close()
            }

            alignment: Qt.AlignHCenter
            padding: 10
        }
    }
}
