// SettingsPage.qml - Ayarlar Sayfası (Full Feature Restoration)
import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Rectangle {
    id: settingsPage
    color: Material.background

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        contentHeight: settingsColumn.height + 60
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn

        ColumnLayout {
            id: settingsColumn
            width: Math.min(parent.width - 48, 1000)
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.top
            anchors.margins: 24
            spacing: 24

            Label {
                text: "⚙️ " + (backend.uiTrigger, backend.getTextWithDefault("nav_settings", "Settings"))
                font.pixelSize: 28
                font.family: root.iconFontFamily
                font.bold: true
                color: root.mainTextColor
            }

            // ==================== GENEL AYARLAR ====================
            SettingsGroup {
                title: "🌐 " + (backend.uiTrigger, backend.getTextWithDefault("settings_general", "General Settings"))
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 16

                    SettingsRow {
                        label: (backend.uiTrigger, backend.getTextWithDefault("ui_language_label", "App Language:"))
                        ComboBox {
                            Layout.fillWidth: true
                            model: settingsBackend ? settingsBackend.getAvailableUILanguages() : []
                            textRole: "name"
                            valueRole: "code"
                            currentIndex: findIndex(model, settingsBackend ? settingsBackend.currentLanguage : "")
                            onActivated: if (settingsBackend) settingsBackend.setUILanguage(currentValue)
                            
                            function findIndex(model, value) {
                                for(var i=0; i<model.length; i++) if(model[i].code === value) return i;
                                return 0;
                            }
                        }
                    }

                    SettingsRow {
                        label: (backend.uiTrigger, backend.getTextWithDefault("theme_menu", "Theme:"))
                        ComboBox {
                            Layout.fillWidth: true
                            model: settingsBackend ? settingsBackend.getAvailableThemes() : []
                            textRole: "name"
                            valueRole: "code"
                            currentIndex: findIndex(model, settingsBackend ? settingsBackend.currentTheme : "")
                            onActivated: if (settingsBackend) settingsBackend.setTheme(currentValue)
                            
                            function findIndex(model, value) {
                                for(var i=0; i<model.length; i++) if(model[i].code === value) return i;
                                return 0;
                            }
                        }
                    }
                    
                    CheckBox {
                        checked: settingsBackend ? settingsBackend.getCheckUpdates() : false
                        onCheckedChanged: if (settingsBackend) settingsBackend.setCheckUpdates(checked)
                        text: (backend.uiTrigger, backend.getTextWithDefault("check_updates", "Automatically check for updates"))
                    }

                    Button {
                        text: "🔄 " + (backend.uiTrigger, backend.getTextWithDefault("check_updates_now_button", "Check for updates now"))
                        font.family: root.iconFontFamily
                        onClicked: backend.checkForUpdates(true)
                        Layout.preferredHeight: 40
                        background: Rectangle {
                            radius: 8
                            color: parent.down ? Qt.darker(Material.accent, 1.2) : parent.hovered ? Qt.darker(Material.accent, 1.1) : Material.accent
                            border.color: root.borderColor
                        }
                    }

                    // --- PORTABLE MODE AYARLARI ---
                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: root.borderColor
                        Layout.topMargin: 8
                        Layout.bottomMargin: 8
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        
                        CheckBox {
                            checked: settingsBackend ? settingsBackend.getPortableMode() : false
                            enabled: settingsBackend ? settingsBackend.isPortableModeSupported() : false
                            opacity: enabled ? 1.0 : 0.5
                            onCheckedChanged: {
                                if (!settingsBackend) return
                                if (checked !== settingsBackend.getPortableMode()) {
                                    var success = settingsBackend.setPortableMode(checked)
                                    if (!success) {
                                        checked = !checked // Revert if failed
                                    }
                                }
                            }
                            text: (backend.uiTrigger, backend.getTextWithDefault("portable_mode_toggle", "Portable Mode (Save data next to exe)"))
                        }
                        
                        Item { Layout.fillWidth: true } // Spacer
                        
                        Button {
                            text: "📁 " + (backend.uiTrigger, backend.getTextWithDefault("open_data_folder_btn", "Open Data Folder"))
                            font.family: root.iconFontFamily
                            onClicked: if (settingsBackend) settingsBackend.openDataFolder()
                            font.pixelSize: 13
                            background: Rectangle {
                                radius: 8
                                color: parent.down ? Qt.darker(root.inputBackground, 1.2) : parent.hovered ? Qt.darker(root.inputBackground, 1.1) : root.inputBackground
                                border.color: root.borderColor
                            }
                        }
                    }
                }
            }

            // ==================== API AYARLARI ====================
            SettingsGroup {
                title: "🔌 " + (backend.uiTrigger, backend.getTextWithDefault("settings_engines_title", "Translation Engines & APIs"))
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 20
                    

                    // DeepL API Key
                    ColumnLayout {
                        spacing: 8
                        Label { text: (backend.uiTrigger, backend.getTextWithDefault("deepl_api_title", "DeepL API Key:")); color: root.secondaryTextColor }
                        TextField {
                            Layout.fillWidth: true
                            echoMode: TextInput.Password
                            text: settingsBackend ? settingsBackend.getDeepLApiKey() : ""
                            onTextChanged: if (settingsBackend) settingsBackend.setDeepLApiKey(text)
                            placeholderText: (backend.uiTrigger, backend.getTextWithDefault("deepl_api_key_placeholder", "API Key (sk-...) or (free:...)"))
                            background: Rectangle { radius: 8; color: root.inputBackground; border.color: root.borderColor }
                        }
                    }
                    
                    RowLayout {
                        spacing: 12
                        Label { text: (backend.uiTrigger, backend.getTextWithDefault("deepl_formality_label", "DeepL Formality:")); color: root.secondaryTextColor; Layout.preferredWidth: 150 }
                        ComboBox {
                            Layout.fillWidth: true
                            model: [
                                {code: "default", name: (backend.uiTrigger, backend.getTextWithDefault("formality_default", "Default"))},
                                {code: "formal", name: (backend.uiTrigger, backend.getTextWithDefault("formality_formal", "Formal"))},
                                {code: "informal", name: (backend.uiTrigger, backend.getTextWithDefault("formality_informal", "Informal"))}
                            ]
                            textRole: "name"
                            valueRole: "code"
                            currentIndex: findIndex(model, settingsBackend ? settingsBackend.getDeepLFormality() : "default")
                            onActivated: if (settingsBackend) settingsBackend.setDeepLFormality(currentValue)
                            function findIndex(model, value) {
                                for(var i=0; i<model.length; i++) if(model[i].code === value) return i;
                                return 0;
                            }
                        }
                    }

                    // OpenAI / OpenRouter Section
                    Label { text: (backend.uiTrigger, backend.getTextWithDefault("openai_section_title", "🤖 OpenAI / OpenRouter / DeepSeek")); font.bold: true; font.family: root.iconFontFamily; color: root.mainTextColor; Layout.topMargin: 10 }
                    
                    // Preset ComboBox
                    RowLayout {
                        spacing: 12
                        Label { text: (backend.uiTrigger, backend.getTextWithDefault("preset_label", "Preset:")); color: root.secondaryTextColor; Layout.preferredWidth: 80 }
                        ComboBox {
                            id: openaiPresetCombo
                            Layout.fillWidth: true
                            model: settingsBackend ? settingsBackend.getOpenAIPresets() : []
                            textRole: "name"
                            onActivated: {
                                var result = settingsBackend.applyOpenAIPreset(currentText)
                                var data = JSON.parse(result)
                                openaiModelField.text = data.model
                                openaiBaseUrlField.text = data.url
                            }
                        }
                    }
                    
                    ApiField { 
                        id: openaiApiKeyField
                        label: (backend.uiTrigger, backend.getTextWithDefault("api_key_label", "API Key")); 
                        text: settingsBackend ? settingsBackend.getOpenAIApiKey() : ""; 
                        onChanged: (newValue) => { if (settingsBackend) settingsBackend.setOpenAIApiKey(newValue) } 
                    }
                    RowLayout {
                        spacing: 12
                        TextField {
                            id: openaiModelField
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            placeholderText: text.length > 0 ? "" : (backend.uiTrigger, backend.getTextWithDefault("placeholder_openai_model", "Model (e.g. gpt-3.5-turbo)"))
                            text: settingsBackend ? settingsBackend.getOpenAIModel() : ""
                            onEditingFinished: if (settingsBackend) settingsBackend.setOpenAIModel(text)
                            leftPadding: 12
                            rightPadding: 12
                            color: root.mainTextColor
                            verticalAlignment: TextInput.AlignVCenter
                            background: Rectangle { radius: 8; color: root.inputBackground; border.color: root.borderColor }
                            placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.45)
                        }
                        TextField {
                            id: openaiBaseUrlField
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            placeholderText: text.length > 0 ? "" : (backend.uiTrigger, backend.getTextWithDefault("placeholder_openai_base_url", "Base URL (Optional)"))
                            text: settingsBackend ? settingsBackend.getOpenAIBaseUrl() : ""
                            onEditingFinished: if (settingsBackend) settingsBackend.setOpenAIBaseUrl(text)
                            leftPadding: 12
                            rightPadding: 12
                            color: root.mainTextColor
                            verticalAlignment: TextInput.AlignVCenter
                            background: Rectangle { radius: 8; color: root.inputBackground; border.color: root.borderColor }
                            placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.45)
                        }

                    }

                    // Gemini Section
                    Label { text: (backend.uiTrigger, backend.getTextWithDefault("gemini_section_title", "✨ Google Gemini")); font.bold: true; font.family: root.iconFontFamily; color: root.mainTextColor; Layout.topMargin: 10 }
                    ApiField { 
                        label: (backend.uiTrigger, backend.getTextWithDefault("gemini_api_key_label", "Gemini API Key")); 
                        text: settingsBackend.getGeminiApiKey(); 
                        onChanged: (newValue) => settingsBackend.setGeminiApiKey(newValue) 
                    }
                    RowLayout {
                        spacing: 12
                        TextField {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 40
                            placeholderText: text.length > 0 ? "" : (backend.uiTrigger, backend.getTextWithDefault("placeholder_gemini_model", "Model (e.g. gemini-2.1-flash)"))
                            text: settingsBackend.getGeminiModel()
                            onEditingFinished: settingsBackend.setGeminiModel(text)
                            leftPadding: 12
                            rightPadding: 12
                            color: root.mainTextColor
                            verticalAlignment: TextInput.AlignVCenter
                            background: Rectangle { radius: 8; color: root.inputBackground; border.color: root.borderColor }
                            placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.45)
                        }
                        ComboBox {
                            Layout.preferredWidth: 200
                            model: [
                                {code: "BLOCK_NONE", name: (backend.uiTrigger, backend.getTextWithDefault("gemini_safety_none", "Off"))},
                                {code: "BLOCK_ONLY_HIGH", name: (backend.uiTrigger, backend.getTextWithDefault("gemini_safety_high", "High"))},
                                {code: "BLOCK_MEDIUM_AND_ABOVE", name: (backend.uiTrigger, backend.getTextWithDefault("gemini_safety_medium", "Medium"))},
                                {code: "BLOCK_LOW_AND_ABOVE", name: (backend.uiTrigger, backend.getTextWithDefault("gemini_safety_low", "Low"))}
                            ]
                            textRole: "name"
                            valueRole: "code"
                            currentIndex: findIndex(model, settingsBackend.getGeminiSafety())
                            onActivated: settingsBackend.setGeminiSafety(currentValue)
                            function findIndex(model, value) {
                                for(var i=0; i<model.length; i++) if(model[i].code === value) return i;
                                return 0;
                            }
                        }
                    }

                    // Local LLM Section
                    Label { text: "🖥️ " + (backend.uiTrigger, backend.getTextWithDefault("settings_local_llm_title", "Local LLM Settings")); font.bold: true; font.family: root.iconFontFamily; color: root.mainTextColor; Layout.topMargin: 10 }
                    Label {
                        text: (backend.uiTrigger, backend.getTextWithDefault("settings_local_llm_desc", "Connect local AI apps (Ollama, LM Studio etc.) for context-aware, highly accurate translations that remember previous lines."))
                        color: "#999"
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.pixelSize: 13
                        bottomPadding: 5
                    }

                    RowLayout {
                         Label { text: (backend.uiTrigger, backend.getTextWithDefault("local_llm_preset_label", "Preset:")); color: "#ccc"; Layout.preferredWidth: 100 }
                         ComboBox {
                             Layout.fillWidth: true
                             model: settingsBackend.getLocalLLMPresets()
                             textRole: "name"
                             onActivated: {
                                 var result = settingsBackend.applyLocalLLMPreset(currentText)
                                 var data = JSON.parse(result)
                                 llmUrlField.text = data.url
                                 llmModelField.text = data.model
                             }
                         }
                    }
                    TextField { 
                        id: llmUrlField; 
                        Layout.fillWidth: true; 
                        Layout.preferredHeight: 40
                        text: settingsBackend.getLocalLLMUrl(); 
                        onEditingFinished: settingsBackend.setLocalLLMUrl(text); 
                        placeholderText: text.length > 0 ? "" : (backend.uiTrigger, backend.getTextWithDefault("local_llm_url_placeholder", "Server URL"))
                        leftPadding: 12; rightPadding: 12; color: root.mainTextColor
                        verticalAlignment: TextInput.AlignVCenter
                        background: Rectangle { radius: 8; color: root.inputBackground; border.color: root.borderColor }
                        placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.45)
                    }
                    TextField { 
                        id: llmModelField; 
                        Layout.fillWidth: true; 
                        Layout.preferredHeight: 40
                        text: settingsBackend.getLocalLLMModel(); 
                        onEditingFinished: settingsBackend.setLocalLLMModel(text); 
                        placeholderText: text.length > 0 ? "" : (backend.uiTrigger, backend.getTextWithDefault("local_llm_model_placeholder", "Model Name"))
                        leftPadding: 12; rightPadding: 12; color: root.mainTextColor
                        verticalAlignment: TextInput.AlignVCenter
                        background: Rectangle { radius: 8; color: root.inputBackground; border.color: root.borderColor }
                        placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.45)
                    }
                    
                    RowLayout {
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("local_llm_timeout_label", "Timeout (sec):")); Layout.fillWidth: true;
                            SpinBox { from: 10; to: 600; value: settingsBackend.getLocalLLMTimeout(); onValueChanged: settingsBackend.setLocalLLMTimeout(value); editable: true }
                        }
                    }

                    Button {
                        text: "🔌 " + (backend.uiTrigger, backend.getTextWithDefault("test_local_llm_connection", "Test Connection"))
                        font.family: root.iconFontFamily
                        Layout.fillWidth: true; highlighted: true
                        onClicked: testResultLabel.text = settingsBackend.testLocalLLMConnection()
                    }
                    Label { id: testResultLabel; Layout.fillWidth: true; color: text.includes("Success") ? "#6bcb77" : "#ff6b6b"; wrapMode: Text.Wrap }

                    // LibreTranslate Section
                    Label { text: "🌐 " + (backend.uiTrigger, backend.getTextWithDefault("settings_libretranslate_title", "LibreTranslate (Local / Self-hosted)")); font.bold: true; font.family: root.iconFontFamily; color: root.mainTextColor; Layout.topMargin: 10 }
                    Label {
                        text: (backend.uiTrigger, backend.getTextWithDefault("settings_libretranslate_desc", "Connect LibreTranslate, Apertium or any compatible local translation server for fully offline, privacy-friendly machine translations."))
                        color: "#999"
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.pixelSize: 13
                        bottomPadding: 5
                    }

                    RowLayout {
                        Label { text: (backend.uiTrigger, backend.getTextWithDefault("libretranslate_preset_label", "Preset:")); color: "#ccc"; Layout.preferredWidth: 100 }
                        ComboBox {
                            Layout.fillWidth: true
                            model: settingsBackend.getLibreTranslatePresets()
                            textRole: "name"
                            onActivated: {
                                var result = settingsBackend.applyLibreTranslatePreset(currentText)
                                var data = JSON.parse(result)
                                libreUrlField.text = data.url
                            }
                        }
                    }

                    TextField {
                        id: libreUrlField
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        text: settingsBackend.getLibreTranslateUrl()
                        onEditingFinished: settingsBackend.setLibreTranslateUrl(text)
                        placeholderText: text.length > 0 ? "" : (backend.uiTrigger, backend.getTextWithDefault("libretranslate_url_placeholder", "Server URL (e.g. http://localhost:5000)"))
                        leftPadding: 12; rightPadding: 12; color: root.mainTextColor
                        verticalAlignment: TextInput.AlignVCenter
                        background: Rectangle { radius: 8; color: root.inputBackground; border.color: root.borderColor }
                        placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.45)
                    }
                    TextField {
                        id: libreApiKeyField
                        Layout.fillWidth: true
                        Layout.preferredHeight: 40
                        text: settingsBackend.getLibreTranslateApiKey()
                        onEditingFinished: settingsBackend.setLibreTranslateApiKey(text)
                        placeholderText: text.length > 0 ? "" : (backend.uiTrigger, backend.getTextWithDefault("libretranslate_api_key_placeholder", "API Key (optional, for managed instances)"))
                        leftPadding: 12; rightPadding: 12; color: root.mainTextColor
                        echoMode: TextInput.Password
                        verticalAlignment: TextInput.AlignVCenter
                        background: Rectangle { radius: 8; color: root.inputBackground; border.color: root.borderColor }
                        placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.45)
                    }
                    Button {
                        text: "🔌 " + (backend.uiTrigger, backend.getTextWithDefault("test_libretranslate_connection", "Test Connection"))
                        font.family: root.iconFontFamily
                        Layout.fillWidth: true; highlighted: true
                        onClicked: libreTestResult.text = settingsBackend.testLibreTranslateConnection()
                    }
                    Label { id: libreTestResult; Layout.fillWidth: true; color: text.includes("✓") ? "#6bcb77" : "#ff6b6b"; wrapMode: Text.Wrap }




                    // Yandex Translate Section
                    Label { text: "🔵 " + (backend.uiTrigger, backend.getTextWithDefault("settings_yandex_title", "Yandex Translate (Free)")); font.bold: true; font.family: root.iconFontFamily; color: root.mainTextColor; Layout.topMargin: 10 }
                    Label {
                        text: (backend.uiTrigger, backend.getTextWithDefault("settings_yandex_desc", "Zero configuration needed — works out of the box. No API key, no URL. Use the button below to verify Yandex servers are reachable from your network (useful behind firewalls or in regions where Yandex may be restricted)."))
                        color: "#999"
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                        font.pixelSize: 13
                        bottomPadding: 5
                    }
                    Button {
                        text: "🔌 " + (backend.uiTrigger, backend.getTextWithDefault("test_yandex_connection", "Test Connection"))
                        font.family: root.iconFontFamily
                        Layout.fillWidth: true; highlighted: true
                        onClicked: yandexTestResult.text = settingsBackend.testYandexConnection()
                    }
                    Label { id: yandexTestResult; Layout.fillWidth: true; color: text.includes("✓") ? "#6bcb77" : "#ff6b6b"; wrapMode: Text.Wrap }
                }
            }

            // ==================== ÇEVİRİ FİLTRELERİ ====================
            SettingsGroup {
                title: "🔍 " + (backend.uiTrigger, backend.getTextWithDefault("translation_filters", "What to translate?"))
                
                GridLayout {
                    columns: 2
                    Layout.fillWidth: true
                    rowSpacing: 10
                    columnSpacing: 20

                    FilterCheck { key: "dialogue"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_dialogue_label", "Dialogues")) }
                    FilterCheck { key: "menu"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_menu_label", "Menu Options")) }
                    FilterCheck { key: "buttons"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_buttons_label", "Buttons")) }
                    FilterCheck { key: "notifications"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_notifications_label", "Notifications")) }
                    FilterCheck { key: "alt_text"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_alt_text_label", "Alt Texts")) }
                    FilterCheck { key: "confirmations"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_confirmations_label", "Confirmations")) }
                    FilterCheck { key: "input_text"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_input_label", "Input Fields")) }
                    FilterCheck { key: "ui"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_ui_label", "UI Texts")) }
                    FilterCheck { key: "gui_strings"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_gui_label", "GUI Strings")) }
                    FilterCheck { key: "style_strings"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_style_label", "Style Strings")) }
                    FilterCheck { key: "renpy_functions"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_renpy_func_label", "Ren'Py Functions")) }
                    FilterCheck { key: "config_strings"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_config_label", "Config Strings")) }
                    FilterCheck { key: "define_strings"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_define_label", "Define Strings")) }
                    FilterCheck { key: "character_names"; label: (backend.uiTrigger, backend.getTextWithDefault("translate_char_label", "Character Names")) }
                }
            }

            // ==================== PERFORMANS & TEKNİK ====================
            SettingsGroup {
                title: "⚡ " + (backend.uiTrigger, backend.getTextWithDefault("settings_network_title", "Network & Performance"))
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    
                    RowLayout {
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("batch_size_label", "Batch Size:")); Layout.fillWidth: true;
                            SpinBox { id: generalBatchSpinBox; from: 1; to: settingsBackend.getBatchSizeMax(); stepSize: 100; value: settingsBackend.getBatchSize(); onValueChanged: settingsBackend.setBatchSize(value); editable: true }
                        }
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("concurrent_threads_label", "Concurrent Threads:")); Layout.fillWidth: true;
                            SpinBox { from: 1; to: 64; value: settingsBackend.getConcurrentThreads(); onValueChanged: settingsBackend.setConcurrentThreads(value); editable: true }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: root.secondaryTextColor
                        font.pixelSize: 12
                        text: {
                            var selectedEngine = backend.selectedEngine
                            var requested = generalBatchSpinBox.value
                            var cap = settingsBackend.getSelectedEngineBatchCap()
                            var effective = settingsBackend.getEffectiveBatchSizeForSelectedEngine()
                            var base = backend.getTextWithDefault(
                                "batch_size_engine_cap_note",
                                "General batch size can be set up to 10000. Google Translate and Yandex use a maximum effective batch size of 1000."
                            )
                            if (cap > 0 && effective < requested) {
                                var extra = backend.getTextWithDefault(
                                    "batch_size_effective_note",
                                    "Current engine will use an effective batch size of {effective}."
                                )
                                return base + "\n" + extra.replace("{effective}", effective)
                            }
                            return base
                        }
                    }

                    RowLayout {
                         CheckBox { 
                             text: (backend.uiTrigger, backend.getTextWithDefault("use_multi_endpoint_label", "Use Multi-Endpoint"))
                             checked: settingsBackend.getUseMultiEndpoint() 
                             onCheckedChanged: settingsBackend.setUseMultiEndpoint(checked) 
                         }
                         CheckBox { 
                             text: (backend.uiTrigger, backend.getTextWithDefault("enable_lingva_fallback_label", "Lingva Fallback"))
                             checked: settingsBackend.getEnableLingvaFallback() 
                             onCheckedChanged: settingsBackend.setEnableLingvaFallback(checked) 
                         }
                    }

                    RowLayout {
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("chunk_size_label", "Context Limit:")); Layout.fillWidth: true;
                            SpinBox { from: 0; to: 50; value: settingsBackend.getContextLimit(); onValueChanged: settingsBackend.setContextLimit(value); editable: true }
                        }
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("max_chars_label", "Maximum Characters:")); Layout.fillWidth: true;
                             SpinBox { from: 1000; to: 2500; stepSize: 100; value: settingsBackend.getMaxCharsPerRequest(); onValueChanged: settingsBackend.setMaxCharsPerRequest(value); editable: true }
                        }
                    }


                    RowLayout {
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("request_delay_label", "Request Delay (sec):")); Layout.fillWidth: true;
                            DoubleSpinBox { 
                                from: 0; to: 1000; stepSize: 10 
                                value: settingsBackend.getRequestDelay() * 100 
                                onValueChanged: settingsBackend.setRequestDelay(value / 100.0) 
                                editable: true 
                            }
                        }
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("timeout_label", "Timeout (sec):")); Layout.fillWidth: true;
                            SpinBox { from: 5; to: 300; value: settingsBackend.getTimeout(); onValueChanged: settingsBackend.setTimeout(value); editable: true }
                        }
                    }

                    RowLayout {
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("max_retries_label", "Max Retries:")); Layout.fillWidth: true;
                             SpinBox { from: 0; to: 10; value: settingsBackend.getMaxRetries(); onValueChanged: settingsBackend.setMaxRetries(value); editable: true }
                        }
                    }

                    // Proxy Settings section inside Network & Performance
                    Label { text: (backend.uiTrigger, backend.getTextWithDefault("group_proxy", "🌐 Proxy Settings")); font.bold: true; color: root.mainTextColor; Layout.topMargin: 10 }
                    
                    DescriptiveCheck { 
                        label: (backend.uiTrigger, backend.getTextWithDefault("proxy_enabled", "Use Proxy"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("enable_proxy_tooltip", ""))
                        checked: settingsBackend.getProxyEnabled()
                        onToggled: (isChecked) => settingsBackend.setProxyEnabled(isChecked)
                    }
                    TextField {
                        Layout.fillWidth: true
                        placeholderText: (backend.uiTrigger, backend.getTextWithDefault("proxy_url_placeholder", "e.g. http://user:pass@host:port"))
                        text: settingsBackend.getProxyUrl()
                        onEditingFinished: settingsBackend.setProxyUrl(text)
                        leftPadding: 12
                        rightPadding: 12
                        color: root.mainTextColor
                        background: Rectangle { 
                            color: root.inputBackground
                            radius: 8
                            border.color: root.borderColor
                            border.width: 1
                        }
                    }

                    // Manual Proxies
                    Label { 
                        text: (backend.uiTrigger, backend.getTextWithDefault("manual_proxies", "Manual Proxies (one per line):")) 
                        color: "#ccc"
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.max(120, manualProxyArea.contentHeight + 24)
                        color: root.inputBackground
                        radius: 8
                        border.color: root.borderColor
                        border.width: 1

                        ScrollView {
                            anchors.fill: parent
                            clip: true
                            ScrollBar.vertical.policy: ScrollBar.AsNeeded

                            TextArea {
                                id: manualProxyArea
                                text: settingsBackend.getManualProxies()
                                placeholderText: "ipp:port\nuser:pass@ip:port"
                                color: root.mainTextColor
                                font.pixelSize: 13
                                wrapMode: TextEdit.NoWrap
                                leftPadding: 12
                                rightPadding: 12
                                topPadding: 12
                                bottomPadding: 12
                                selectByMouse: true
                                background: null // Container handles the background
                                
                                onTextChanged: manualProxySaveTimer.restart()
                                onActiveFocusChanged: if (!activeFocus) { manualProxySaveTimer.stop(); settingsBackend.setManualProxies(text) }
                                Component.onDestruction: settingsBackend.setManualProxies(text)
                                
                                // Placeholder style fix
                                placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.35)
                            }

                            Timer {
                                id: manualProxySaveTimer
                                interval: 500
                                repeat: false
                                onTriggered: settingsBackend.setManualProxies(manualProxyArea.text)
                            }
                        }
                    }

                    // Refresh Button & Status
                    RowLayout {
                        Button {
                            id: proxyRefreshBtn
                            text: (backend.uiTrigger, backend.getTextWithDefault("refresh_proxies_btn", "Test Connections"))
                            onClicked: {
                                enabled = false
                                proxyStatusLabel.text = (backend.uiTrigger, backend.getTextWithDefault("proxy_refreshing", "Testing..."))
                                proxyStatusLabel.color = "#f39c12" // orange
                                settingsBackend.refreshProxies()
                            }
                        }
                        Label {
                            id: proxyStatusLabel
                            text: ""
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                    }

                    Connections {
                        target: settingsBackend
                        function onProxyRefreshFinished(success, msg) {
                            proxyRefreshBtn.enabled = true
                            proxyStatusLabel.text = msg
                            proxyStatusLabel.color = success ? "#2ecc71" : "#e74c3c"
                        }
                    }
                }
            }

            // ==================== AI MODEL PARAMETRELERİ ====================
            SettingsGroup {
                title: "🧠 " + (backend.uiTrigger, backend.getTextWithDefault("settings_ai_tuning_title", "AI Tuning & Parameters"))
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    
                    // AI Uyarı Mesajları
                    Rectangle {
                        Layout.fillWidth: true
                        height: warningCol.height + 16
                        radius: 8
                        color: "#2d1a1a"
                        border.color: "#e74c3c"
                        
                        ColumnLayout {
                            id: warningCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 8
                            spacing: 4
                            Label { text: (backend.uiTrigger, backend.getTextWithDefault("ai_hallucination_warning", "⚠️ WARNING: Small models may hallucinate.")); color: "#e74c3c"; font.pixelSize: 12; wrapMode: Text.Wrap }
                            Label { text: (backend.uiTrigger, backend.getTextWithDefault("ai_vram_warning", "⚠️ WARNING: 4GB+ VRAM recommended for Local LLM.")); color: "#e74c3c"; font.pixelSize: 12; wrapMode: Text.Wrap }
                            Label { text: (backend.uiTrigger, backend.getTextWithDefault("ai_source_lang_warning", "💡 TIP: Specifying source language improves quality.")); color: "#3498db"; font.pixelSize: 12; wrapMode: Text.Wrap }
                        }
                    }
                    
                    // Sıcaklık (Temperature)
                    ColumnLayout {
                        Layout.fillWidth: true
                        RowLayout {
                             Label { text: (backend.uiTrigger, backend.getTextWithDefault("ai_creativity_label", "Creativity (Temperature):")); color: "#ccc" }
                             Label { text: tempSlider.value.toFixed(1); color: Material.accent; font.bold: true }
                        }
                        Slider {
                            id: tempSlider
                            Layout.fillWidth: true
                            from: 0.0
                            to: 2.0
                            value: settingsBackend.getAITemperature()
                            onMoved: settingsBackend.setAITemperature(value)
                        }
                    }

                    // Tokens & Timeout
                    RowLayout {
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("ai_tokens_short", "Max Tokens:")); Layout.fillWidth: true;
                            SpinBox { from: 256; to: 128000; stepSize: 256; value: settingsBackend.getAIMaxTokens(); onValueChanged: settingsBackend.setAIMaxTokens(value); editable: true }
                        }
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("local_llm_timeout_label", "Timeout (sec):")); Layout.fillWidth: true;
                            SpinBox { from: 10; to: 300; value: settingsBackend.getAITimeout(); onValueChanged: settingsBackend.setAITimeout(value); editable: true }
                        }
                    }

                    // AI Batch & Concurrency (New!)
                    RowLayout {
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("ai_batch_important_label", "AI Batch Size:")); Layout.fillWidth: true;
                            SpinBox { 
                                id: aiBatchSpinBox
                                from: 1; to: settingsBackend.getAIBatchSizeMax(); stepSize: 100;
                                value: settingsBackend.getAIBatchSize(); 
                                onValueChanged: settingsBackend.setAIBatchSize(value); 
                                editable: true 
                            }
                        }
                        SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("ai_parallel_label", "AI Parallel Requests:")); Layout.fillWidth: true;
                            SpinBox { from: 1; to: 10; value: settingsBackend.getAIConcurrency(); onValueChanged: settingsBackend.setAIConcurrency(value); editable: true }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: root.secondaryTextColor
                        font.pixelSize: 12
                        text: {
                            var base = backend.getTextWithDefault(
                                "ai_batch_limit_note",
                                "AI batch size can also be set up to 10000, but very large values may increase token usage, latency, and API failure risk."
                            )
                            if ((backend.selectedEngine === "openai" || backend.selectedEngine === "gemini" || backend.selectedEngine === "deepseek" || backend.selectedEngine === "local_llm")
                                    && aiBatchSpinBox.value > 1000) {
                                var extra = backend.getTextWithDefault(
                                    "ai_batch_large_warning",
                                    "Current AI batch size is very high; if you see timeouts, quota spikes, or failed requests, lower it."
                                )
                                return base + "\n" + extra
                            }
                            return base
                        }
                    }

                    RowLayout {
                         SettingsRow { label: (backend.uiTrigger, backend.getTextWithDefault("ai_request_delay_label_sec", "AI Request Delay (sec):")); Layout.fillWidth: true;
                            DoubleSpinBox { 
                                from: 0; to: 2000; stepSize: 10 
                                value: settingsBackend.getAIRequestDelay() * 100 
                                onValueChanged: settingsBackend.setAIRequestDelay(value / 100.0) 
                                editable: true 
                            }
                        }
                    }

                    // System Prompt
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Label { 
                            text: (backend.uiTrigger, backend.getTextWithDefault("settings_ai_prompt_title", "Custom System Prompt (Optional):"))
                            color: "#ccc" 
                            font.bold: true
                        }
                        
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 120
                            color: root.inputBackground
                            radius: 8
                            border.color: root.borderColor
                            border.width: 1

                            ScrollView {
                                anchors.fill: parent
                                clip: true
                                TextArea {
                                    id: aiPromptArea
                                    text: settingsBackend.getAISystemPrompt()
                                    onTextChanged: aiPromptSaveTimer.restart()
                                    onActiveFocusChanged: if (!activeFocus) { aiPromptSaveTimer.stop(); settingsBackend.setAISystemPrompt(text) }
                                    Component.onDestruction: settingsBackend.setAISystemPrompt(text)
                                    placeholderText: (backend.uiTrigger, backend.getTextWithDefault("settings_ai_prompt_desc", "Override default instructions for AI..."))
                                    color: root.mainTextColor
                                    font.pixelSize: 13
                                    wrapMode: TextEdit.Wrap
                                    leftPadding: 12
                                    rightPadding: 12
                                    topPadding: 12
                                    bottomPadding: 12
                                    selectByMouse: true
                                    background: null
                                    placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.35)
                                }

                                Timer {
                                    id: aiPromptSaveTimer
                                    interval: 500
                                    repeat: false
                                    onTriggered: settingsBackend.setAISystemPrompt(aiPromptArea.text)
                                }
                            }
                        }
                    }
                }
            }

            // ==================== SİSTEM & TEKNİK AYARLAR ====================
            SettingsGroup {
                title: "🛠️ " + (backend.uiTrigger, backend.getTextWithDefault("settings_system_title", "System & Technical Settings"))
                
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    
                    CheckBox { 
                        text: (backend.uiTrigger, backend.getTextWithDefault("settings_use_html_protection", "HTML Wrap Protection (Zenpy-Style)"))
                        checked: settingsBackend.getUseHtmlProtection() 
                        enabled: backend.selectedEngine !== "google"
                        onCheckedChanged: if (enabled) settingsBackend.setUseHtmlProtection(checked)
                        ToolTip.visible: hovered
                        ToolTip.text: enabled
                            ? (backend.uiTrigger, backend.getTextWithDefault("tooltip_html_protection", "Protects placeholders without breaking them. Uses Google Translate's <span class='notranslate'> tag."))
                            : (backend.uiTrigger, backend.getTextWithDefault("tooltip_html_protection_google_disabled", "Disabled for Google web endpoint. Token-based placeholder protection is used automatically."))
                    }

                    DescriptiveCheck { 
                        label: (backend.uiTrigger, backend.getTextWithDefault("scan_rpym_files", "Scan .rpym Files"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("scan_rpym_files_desc", ""))
                        checked: settingsBackend.getScanRpymFiles()
                        onToggled: (isChecked) => settingsBackend.setScanRpymFiles(isChecked)
                    }

                    DescriptiveCheck { 
                        label: (backend.uiTrigger, backend.getTextWithDefault("use_cache_label", "Use Translation Memory"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("use_cache_desc", ""))
                        checked: settingsBackend.getUseCache()
                        onToggled: (isChecked) => settingsBackend.setUseCache(isChecked)
                    }

                    DescriptiveCheck { 
                        label: (backend.uiTrigger, backend.getTextWithDefault("use_global_cache", "Global TM (Portable)"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("use_global_cache_desc", ""))
                        checked: settingsBackend.getUseGlobalCache()
                        onToggled: (isChecked) => settingsBackend.setUseGlobalCache(isChecked)
                    }

                    DescriptiveCheck { 
                        label: (backend.uiTrigger, backend.getTextWithDefault("exclude_system_folders", "Exclude System Folders"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("exclude_system_folders_desc", ""))
                        checked: settingsBackend.getExcludeSystemFolders()
                        onToggled: (isChecked) => settingsBackend.setExcludeSystemFolders(isChecked)
                    }
                    
                    DescriptiveCheck { 
                        label: (backend.uiTrigger, backend.getTextWithDefault("aggressive_retry", "Aggressive Translation"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("aggressive_retry_desc", ""))
                        checked: settingsBackend.getAggressiveRetry()
                        onToggled: (isChecked) => settingsBackend.setAggressiveRetry(isChecked)
                    }

                    DescriptiveCheck { 
                        label: (backend.uiTrigger, backend.getTextWithDefault("show_debug_engines", "Show Debug Engines"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("show_debug_engines_desc", ""))
                        checked: settingsBackend.getShowDebugEngines()
                        onToggled: (isChecked) => settingsBackend.setShowDebugEngines(isChecked)
                    }

                    DescriptiveCheck {
                        label: (backend.uiTrigger, backend.getTextWithDefault("runtime_string_diagnostics", "Log Missed Runtime Strings"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("runtime_string_diagnostics_desc", "Write bounded diagnostics for runtime text that stays untranslated. Useful for sandbox games and dynamic UI debugging."))
                        checked: settingsBackend.getRuntimeStringDiagnostics()
                        onToggled: (isChecked) => settingsBackend.setRuntimeStringDiagnostics(isChecked)
                    }

                    DescriptiveCheck {
                        label: (backend.uiTrigger, backend.getTextWithDefault("auto_hook_gen", "Auto-Generate Hook After Translation"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("auto_hook_gen_desc", ""))
                        checked: settingsBackend.getAutoHook()
                        onToggled: (isChecked) => settingsBackend.setAutoHook(isChecked)
                    }

                    DescriptiveCheck { 
                        label: (backend.uiTrigger, backend.getTextWithDefault("auto_unren", "Automatic RPA Extraction"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("auto_unren_desc", ""))
                        checked: settingsBackend.getAutoUnren()
                        onToggled: (isChecked) => settingsBackend.setAutoUnren(isChecked)
                    }

                    DescriptiveCheck {
                        label: (backend.uiTrigger, backend.getTextWithDefault("auto_protect_char_names", "Auto-Protect Character Names"))
                        description: (backend.uiTrigger, backend.getTextWithDefault("auto_protect_char_names_desc", "Automatically protect character names from translation"))
                        checked: settingsBackend.getAutoProtectCharNames()
                        onToggled: (isChecked) => settingsBackend.setAutoProtectCharNames(isChecked)
                    }



                    // Custom Function Params (JSON)
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Label {
                            text: (backend.uiTrigger, backend.getTextWithDefault("custom_function_params_label", "Custom Function Params (JSON):"))
                            color: "#ccc"
                            font.bold: true
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                        Label {
                            text: (backend.uiTrigger, backend.getTextWithDefault("custom_function_params_desc", "Define which custom Ren'Py functions should have their text parameters extracted for translation."))
                            color: root.secondaryTextColor
                            font.pixelSize: 12
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: Math.max(80, customFuncArea.contentHeight + 24)
                            color: root.inputBackground
                            radius: 8
                            border.color: root.borderColor
                            border.width: 1
                            ScrollView {
                                anchors.fill: parent
                                clip: true
                                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                                TextArea {
                                    id: customFuncArea
                                    text: settingsBackend.getCustomFunctionParams()
                                    placeholderText: '{"MyFunc": {"pos": [0, 1]}, "notify": {"pos": [0]}}'
                                    color: root.mainTextColor
                                    font.pixelSize: 13
                                    font.family: "Consolas"
                                    wrapMode: TextEdit.Wrap
                                    leftPadding: 12; rightPadding: 12; topPadding: 12; bottomPadding: 12
                                    selectByMouse: true
                                    background: null
                                    onTextChanged: customFuncSaveTimer.restart()
                                    onActiveFocusChanged: if (!activeFocus) { customFuncSaveTimer.stop(); settingsBackend.setCustomFunctionParams(text) }
                                    Component.onDestruction: settingsBackend.setCustomFunctionParams(text)
                                    placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.35)
                                }

                                Timer {
                                    id: customFuncSaveTimer
                                    interval: 500
                                    repeat: false
                                    onTriggered: settingsBackend.setCustomFunctionParams(customFuncArea.text)
                                }
                            }
                        }
                    }
                }
            }

            // Reset Button
            Button {
                text: (backend.uiTrigger, backend.getTextWithDefault("restore_defaults_full", "♻️ Restore All Settings to Default"))
                font.family: root.iconFontFamily
                Layout.alignment: Qt.AlignRight
                flat: true; Material.foreground: Material.Red
                onClicked: {
                    settingsBackend.restoreDefaults()
                    backend.refreshUI()
                }
            }
        }
    }

    // Helper Components
    component SettingsGroup: Rectangle {
        property string title: ""
        default property alias content: innerLayout.children
        Layout.fillWidth: true
        implicitHeight: innerLayout.height + 40
        radius: 12
        color: root.cardBackground
        ColumnLayout {
            id: innerLayout
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 20; spacing: 16
            Label { text: title; font.pixelSize: 18; font.family: root.iconFontFamily; font.bold: true; color: Material.accent }
            Rectangle { Layout.fillWidth: true; height: 1; color: root.separatorColor }
        }
    }

    component SettingsRow: RowLayout {
        property string label: ""
        spacing: 20
        Label { text: label; Layout.preferredWidth: 200; color: root.secondaryTextColor }
    }

    component FilterCheck: CheckBox {
        property string key: ""
        property string label: ""
        text: label
        checked: settingsBackend.getFilter(key)
        onCheckedChanged: settingsBackend.setFilter(key, checked)
        Layout.fillWidth: true
    }

    component DescriptiveCheck: RowLayout {
        property string label: ""
        property string description: ""
        property bool checked: false
        signal toggled(bool isChecked)

        spacing: 12
        Layout.fillWidth: true

        CheckBox {
            id: cb
            checked: parent.checked
            onCheckedChanged: parent.toggled(checked)
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: -8
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            Label {
                text: label
                color: root.mainTextColor
                font.bold: true
                font.pixelSize: 14
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                MouseArea {
                    anchors.fill: parent
                    onClicked: cb.checked = !cb.checked
                }
            }
            Label {
                text: description
                color: root.secondaryTextColor
                font.pixelSize: 11
                wrapMode: Text.Wrap
                Layout.fillWidth: true
                opacity: 0.7
            }
        }
    }

    component DoubleSpinBox: SpinBox {
        property int decimals: 2
        property real realValue: value / 100.0

        from: 0
        to: 1000
        stepSize: 10
        editable: true

        validator: DoubleValidator {
            bottom: Math.min(from, to)
            top: Math.max(from, to)
        }

        textFromValue: function(value, locale) {
            return Number(value / 100.0).toLocaleString(locale, 'f', decimals)
        }

        valueFromText: function(text, locale) {
            return Number.fromLocaleString(locale, text) * 100
        }
    }

    component ApiField: ColumnLayout {
        property string label: ""
        property string text: ""
        signal changed(string newValue)
        Label { text: label; color: "#ccc"; font.bold: true }
        TextField {
            Layout.fillWidth: true; 
            Layout.preferredHeight: 40
            echoMode: TextInput.Password; 
            text: parent.text; 
            onTextChanged: parent.changed(text)
            leftPadding: 12; rightPadding: 12; color: root.mainTextColor
            verticalAlignment: TextInput.AlignVCenter
            background: Rectangle { color: root.inputBackground; radius: 8; border.color: root.borderColor }
            placeholderTextColor: Qt.rgba(root.mainTextColor.r, root.mainTextColor.g, root.mainTextColor.b, 0.35)
        }
    }
}
