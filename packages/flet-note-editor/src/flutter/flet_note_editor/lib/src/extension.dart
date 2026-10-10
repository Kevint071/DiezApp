import 'package:flet/flet.dart';
import 'package:flutter/widgets.dart';

import 'note_editor.dart';

class Extension extends FletExtension {
  @override
  Widget? createWidget(Key? key, Control control) {
    switch (control.type) {
      case "NoteEditor":
        return NoteEditorControl(key: key, control: control);
      default:
        return null;
    }
  }
}
