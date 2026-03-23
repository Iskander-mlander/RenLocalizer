
init python:
    gallery = Gallery()
    gallery.button("Unlockable Gallery Item") # Should this be extracted? Currently probably not.
    
    class MyCustomUI:
        def show_msg(self, msg):
            pass

    my_ui = MyCustomUI()
    my_ui.show_msg("This is a custom message") # Likely missed.

define MC_NAME = "Rhiannon" # Should this be extracted? Currently blacklisted due to uppercase.

screen custom_menu:
    textbutton "Unwrapped String" action NullAction() # Captured by regex.
    text _("Wrapped String") # Captured by regex.
    
    # Tooltip property
    textbutton "Hover Me" action NullAction() tooltip "I am a tooltip" # tooltip property captured?
