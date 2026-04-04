// GlossaryPage.qml - Sözlük Yönetimi Sayfası (Full Logic)
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs

Rectangle {
    id: glossaryPage
    color: Material.background
    
    // Model: Backend'den çekilen veriyi tutar
    ListModel {
        id: glossaryModel
    }

    // Backend iletişimi ve veri yenileme
    function refreshData() {
        glossaryModel.clear()
        var items = backend.getGlossaryItems()
        for(var i=0; i<items.length; i++) {
            glossaryModel.append(items[i])
        }
    }

    Component.onCompleted: refreshData()
    
    // Backend loglarını dinle, gerekirse refresh yap
    Connections {
        target: backend
        function onLogMessage(level, msg) {
            // Refresh on any glossary-related action (language-independent keywords)
            var lowerMsg = msg.toLowerCase()
            if (lowerMsg.includes("glossary") || lowerMsg.includes("terim") || lowerMsg.includes("sözlük") ||
                lowerMsg.includes("added") || lowerMsg.includes("translated") || lowerMsg.includes("removed") ||
                lowerMsg.includes("eklendi") || lowerMsg.includes("çevrildi") || lowerMsg.includes("silindi")) {
                refreshData()
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 20

        // ==================== HEADER ====================
        RowLayout {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            
            Label {
                text: "📚"
                font.pixelSize: 22
                font.family: root.iconFontFamily
                font.bold: true
                color: root.mainTextColor
                Layout.alignment: Qt.AlignVCenter
            }

            Label {
                Layout.fillWidth: true
                text: (backend.uiTrigger, backend.getTextWithDefault("nav_glossary", "Glossary Management"))
                font.pixelSize: 22
                font.bold: true
                color: root.mainTextColor
                wrapMode: Text.WordWrap
                elide: Text.ElideRight
            }
            
            Item { Layout.fillWidth: true }
            
            Button {
                text: "✨ " + (backend.uiTrigger, backend.getTextWithDefault("glossary_extract_btn", "Auto Extract"))
                font.family: root.iconFontFamily
                font.pixelSize: 12
                padding: 6
                onClicked: {
                    var result = backend.extractGlossaryTerms()
                    // Sonuç zaten logMessage ile geliyor ama direkt de gösterebiliriz
                    if (result.includes("Hata") || result.includes("Error")) {
                        console.error(result)
                    }
                }
                Material.background: Material.BlueGrey
            }
            
            Button {
                text: "➕ " + (backend.uiTrigger, backend.getTextWithDefault("edit_add", "Add"))
                font.family: root.iconFontFamily
                font.pixelSize: 12
                padding: 6
                highlighted: true
                onClicked: addDialog.open()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: dashboardRow.implicitHeight + 28
            radius: 12
            color: root.inputBackground
            border.color: root.borderColor
            border.width: 1

            RowLayout {
                id: dashboardRow
                anchors.fill: parent
                anchors.margins: 14
                spacing: 14

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4
                    Label {
                        text: (backend.uiTrigger, backend.getTextWithDefault("glossary_dashboard_desc", "Manage preferred terms, fill empty entries from source text, and keep frequently used translations consistent."))
                        color: root.mainTextColor
                        wrapMode: Text.WordWrap
                        font.pixelSize: 13
                        maximumLineCount: 2
                    }
                }

                Rectangle { width: 1; Layout.fillHeight: true; color: root.borderColor }

                ColumnLayout {
                    spacing: 4
                    Label {
                        text: (backend.uiTrigger, backend.getTextWithDefault("glossary_dashboard_total", "Total Terms"))
                        color: root.secondaryTextColor
                        font.pixelSize: 11
                        font.bold: true
                    }
                    Label {
                        text: glossaryModel.count
                        color: Material.accent
                        font.pixelSize: 20
                        font.bold: true
                    }
                }
            }
        }
        
        // ==================== TOOLBAR ====================
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Button {
                text: "🔄 " + (backend.uiTrigger, backend.getTextWithDefault("btn_translate_empty", "Translate Empty"))
                font.family: root.iconFontFamily
                font.pixelSize: 12
                padding: 6
                onClicked: backend.translateEmptyGlossaryItems()
                flat: true
            }
            
            Button {
                text: "📝 " + (backend.uiTrigger, backend.getTextWithDefault("btn_copy_source", "Copy Source"))
                font.family: root.iconFontFamily
                font.pixelSize: 12
                padding: 6
                onClicked: backend.fillEmptyGlossaryWithSource()
                flat: true
            }
            
            Item { Layout.fillWidth: true }
            
            Label {
                text: (backend.uiTrigger, backend.getTextWithDefault("total_count_label", "Total: {count}")).replace("{count}", glossaryModel.count)
                color: "#666"
                font.pixelSize: 12
            }
        }
        
        // ==================== EXPORT/IMPORT TOOLBAR ====================
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Button {
                text: "📤 " + (backend.uiTrigger, backend.getTextWithDefault("btn_export_glossary", "Export"))
                font.family: root.iconFontFamily
                font.pixelSize: 12
                padding: 6
                flat: true
                onClicked: exportDialog.open()
            }
            
            Button {
                text: "📥 " + (backend.uiTrigger, backend.getTextWithDefault("btn_import_glossary", "Import"))
                font.family: root.iconFontFamily
                font.pixelSize: 12
                padding: 6
                flat: true
                onClicked: importDialog.open()
            }
        }

        // ==================== TABLE HEADERS ====================
        Rectangle {
            Layout.fillWidth: true
            height: 40
            color: root.cardBackground
            radius: 8
            
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 16
                spacing: 8

                Label { text: (backend.uiTrigger, backend.getTextWithDefault("glossary_source", "Source Text")); color: root.secondaryTextColor; font.bold: true; Layout.preferredWidth: 220 }
                Rectangle { width: 1; height: 20; color: root.separatorColor }
                Label { text: (backend.uiTrigger, backend.getTextWithDefault("glossary_target", "Translation")); color: root.secondaryTextColor; font.bold: true; Layout.fillWidth: true }
                Rectangle { width: 1; height: 20; color: root.separatorColor }
                Label { text: (backend.uiTrigger, backend.getTextWithDefault("action", "Action")); color: root.secondaryTextColor; font.bold: true; Layout.preferredWidth: 60 }
            }
        }

        // ==================== LIST (TABLE BODY) ====================
        ListView {
            id: glossaryList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: glossaryModel
            spacing: 6
            
            delegate: Rectangle {
                width: ListView.view.width
                height: Math.max(66, rowContent.implicitHeight + 18)
                color: index % 2 === 0 ? root.inputBackground : root.cardBackground
                radius: 8
                border.width: 0
                
                RowLayout {
                    id: rowContent
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    spacing: 10
                    
                    // Source
                    Label { 
                        text: model.source
                        color: root.mainTextColor
                        font.bold: true
                        Layout.preferredWidth: 210
                        Layout.alignment: Qt.AlignVCenter
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight 
                    }
                    
                    Rectangle { width: 1; Layout.fillHeight: true; color: root.separatorColor }
                    
                    // Target (Editable-like look but currently view-only in list, edit via delete/re-add for MVP)
                    Label { 
                        text: model.target ? model.target : (backend.uiTrigger, backend.getTextWithDefault("empty_placeholder", "<empty>"))
                        color: model.target ? Material.accent : "#555"
                        font.italic: !model.target
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight 
                    }
                    
                    Rectangle { width: 1; Layout.fillHeight: true; color: root.separatorColor }
                    
                    // Delete Button
                    Button {
                        text: "❌"
                        font.family: root.iconFontFamily
                        flat: true
                        Layout.preferredWidth: 34
                        Layout.alignment: Qt.AlignVCenter
                        onClicked: {
                            backend.removeGlossaryItem(model.source)
                            glossaryModel.remove(index)
                        }
                    }
                }
            }
        }
    }
    
    // ==================== ADD DIALOG ====================
    Dialog {
        id: addDialog
        title: (backend.uiTrigger, backend.getTextWithDefault("glossary_add_title", "Add Term"))
        anchors.centerIn: parent
        modal: true
        width: Math.min(400, root.width * 0.85)
        
        property alias sourceText: sourceField.text
        property alias targetText: targetField.text
        
        onOpened: {
            sourceField.text = ""
            targetField.text = ""
            sourceField.forceActiveFocus()
        }
        
        background: Rectangle { color: root.cardBackground; radius: 12; border.color: root.borderColor }
        header: Label { 
            text: (backend.uiTrigger, backend.getTextWithDefault("glossary_add_title", "Add Term"))
            padding: 20
            font.bold: true
            font.pixelSize: 18
            color: root.mainTextColor 
        }
        
        contentItem: ColumnLayout {
            spacing: 15
            
            Label { text: (backend.uiTrigger, backend.getTextWithDefault("glossary_source_hint", "Source (e.g. Sword)")); color: root.secondaryTextColor }
            TextField { 
                id: sourceField
                Layout.fillWidth: true
                color: root.mainTextColor 
                background: Rectangle { color: root.inputBackground; radius: 6; border.color: root.borderColor }
            }
            
            Label { text: (backend.uiTrigger, backend.getTextWithDefault("glossary_target_hint", "Translation (e.g. Sword Translation)")); color: root.secondaryTextColor }
            TextField { 
                id: targetField
                Layout.fillWidth: true
                color: root.mainTextColor
                background: Rectangle { color: root.inputBackground; radius: 6; border.color: root.borderColor }
            }
        }
        
        footer: DialogButtonBox {
            background: Rectangle { color: "transparent" }
            Button { 
                text: (backend.uiTrigger, backend.getTextWithDefault("btn_cancel", "Cancel"))
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                flat: true 
            }
            Button { 
                text: (backend.uiTrigger, backend.getTextWithDefault("btn_save", "Save"))
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                highlighted: true

                onClicked: {
                    backend.addGlossaryItem(addDialog.sourceText, addDialog.targetText)
                    refreshData() // Listeyi güncelle
                }
            }
        }
    }


    // ==================== FILE DIALOGS ====================
    FileDialog {
        id: importDialog
        title: (backend.uiTrigger, backend.getTextWithDefault("dialog_import_glossary", "Import Glossary"))
        nameFilters: ["Data Files (*.xlsx *.xls *.csv *.json)", "Excel Files (*.xlsx *.xls)", "CSV Files (*.csv)", "JSON Files (*.json)", "All Files (*)"]
        fileMode: FileDialog.OpenFile
        onAccepted: {
            var msg = backend.importGlossary(importDialog.selectedFile.toString())
            if (msg === "") {
                 refreshData()
            }
        }
    }

    FileDialog {
        id: exportDialog
        title: (backend.uiTrigger, backend.getTextWithDefault("dialog_export_glossary", "Export Glossary"))
        nameFilters: ["Excel Files (*.xlsx)", "CSV Files (*.csv)", "JSON Files (*.json)"]
        fileMode: FileDialog.SaveFile
        defaultSuffix: "xlsx"
        onAccepted: {
            // Determine format from filter or extension
            var path = exportDialog.selectedFile.toString()
            var format = "xlsx" // default
            if (path.endsWith(".csv")) format = "csv"
            else if (path.endsWith(".json")) format = "json"
            else if (path.endsWith(".xlsx")) format = "xlsx"
            
            backend.exportGlossary(path, format)
        }
    }
}
