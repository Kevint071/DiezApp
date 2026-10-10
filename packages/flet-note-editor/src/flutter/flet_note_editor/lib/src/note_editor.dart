import 'dart:async';
import 'dart:convert';

import 'package:flet/flet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_quill/flutter_quill.dart';

/// Typefaces offered in the "Aa" panel. The app registers the families
/// through `page.fonts`; `null` is the platform default.
const _fonts = <(String?, String)>[
  (null, 'Normal'),
  ('Nunito', 'Redonda'),
  ('Lora', 'Clásica'),
  ('JetBrains Mono', 'Máquina'),
  ('Caveat', 'A mano'),
];

/// Character formats "Quitar formato" removes.
final List<Attribute> _inlineKeys = [
  Attribute.bold,
  Attribute.italic,
  Attribute.underline,
  Attribute.strikeThrough,
  Attribute.font,
];

final _wordChar = RegExp(r"[\p{L}\p{N}_'’]", unicode: true);

/// One indent level, like a tab stop.
const _indentStep = 24.0;

/// Room for "•" or the checkbox plus the gap before the text.
const _markerWidth = 24.0;

/// Room for "1." and each extra digit beyond the first.
const _digitWidth = 9.0;

int _indentLevel(Map<String, Attribute> attrs) =>
    (attrs[Attribute.indent.key]?.value as int?) ?? 0;

/// Lists start flush with the paragraphs instead of Quill's 2em gutter; the
/// text after the marker is what moves right.
HorizontalSpacing _blockIndent(Block block, BuildContext context, int count,
    LeadingBlockNumberPointWidth numberPointWidth) {
  final attrs = block.style.attributes;
  if (attrs.containsKey(Attribute.codeBlock.key)) {
    return TextBlockUtils.defaultIndentWidthBuilder(
        block, context, count, numberPointWidth);
  }
  final indent = _indentStep * _indentLevel(attrs);
  final list = attrs[Attribute.list.key];
  if (list == null) return HorizontalSpacing(indent, 0);
  final marker = list == Attribute.ol
      ? _markerWidth + _digitWidth * ('$count'.length - 1)
      : _markerWidth;
  return HorizontalSpacing(indent + marker, 0);
}

/// Draws bullets and numbers at the start of their indent instead of
/// right-aligned against the text. Checkboxes keep Quill's widget, which
/// already hugs the text.
Widget? _listMarker(Node node, LeadingConfig config) {
  final String label;
  if (config.attribute == Attribute.ul) {
    label = '•';
  } else if (config.attribute == Attribute.ol) {
    // The getter advances the per-level counters; read it once per line.
    label = '${config.getIndexNumberByIndent}.';
  } else {
    return null;
  }
  return Padding(
    padding: EdgeInsetsDirectional.only(
        start: _indentStep * _indentLevel(config.attrs)),
    child: Align(
      alignment: AlignmentDirectional.topStart,
      child: Text(label, style: config.style, softWrap: false),
    ),
  );
}

class NoteEditorControl extends StatefulWidget {
  final Control control;

  NoteEditorControl({Key? key, required this.control})
      : super(key: key ?? ValueKey("control_${control.id}"));

  @override
  State<NoteEditorControl> createState() => _NoteEditorControlState();
}

class _NoteEditorControlState extends State<NoteEditorControl> {
  late QuillController _quill;
  StreamSubscription<DocChange>? _changes;
  final _editorFocus = FocusNode();
  final _scroll = ScrollController();
  final _title = TextEditingController();
  String _value = "";
  String _titleValue = "";
  bool _canUndo = false;
  bool _canRedo = false;
  bool _stylePanelOpen = false;

  Control get control => widget.control;

  @override
  void initState() {
    super.initState();
    _titleValue = control.getString("title", "")!;
    _title.text = _titleValue;
    _quill = QuillController(
      document: _documentFrom(control.getString("value", "")!),
      selection: const TextSelection.collapsed(offset: 0),
      readOnly: control.getBool("read_only", false)!,
    );
    _value = _encode();
    _listenToDocument();
    _quill.addListener(_syncHistory);
    control.addInvokeMethodListener(_invokeMethod);
  }

  @override
  void didUpdateWidget(covariant NoteEditorControl oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Python only rewrites these to load a different note; while typing they
    // come back equal to what this widget already sent.
    final value = control.getString("value", "")!;
    if (value.isNotEmpty && value != _value) {
      _value = value;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        _quill.document = _documentFrom(value);
        _listenToDocument();
        _syncHistory();
      });
    }
    final title = control.getString("title", "")!;
    if (title != _titleValue) {
      _titleValue = title;
      _title.text = title;
    }
  }

  @override
  void dispose() {
    control.removeInvokeMethodListener(_invokeMethod);
    _changes?.cancel();
    _quill.removeListener(_syncHistory);
    _quill.dispose();
    _editorFocus.dispose();
    _scroll.dispose();
    _title.dispose();
    super.dispose();
  }

  // ── Sync with Python ──────────────────────────────────

  static Document _documentFrom(String json) {
    if (json.isEmpty) return Document();
    try {
      return Document.fromJson(jsonDecode(json) as List);
    } catch (e) {
      debugPrint("NoteEditor: invalid delta ($e)");
      return Document();
    }
  }

  String _encode() => jsonEncode(_quill.document.toDelta().toJson());

  void _listenToDocument() {
    _changes?.cancel();
    _changes = _quill.document.changes.listen((change) {
      if (change.source == ChangeSource.local) _publish();
    });
  }

  void _publish() {
    final value = _encode();
    if (value == _value) return;
    _value = value;
    control.updateProperties({"value": value});
    _sendChange();
  }

  void _sendChange() {
    control.triggerEvent("change", {"title": _titleValue, "delta": _value});
  }

  void _onTitleChanged(String title) {
    _titleValue = title;
    control.updateProperties({"title": title});
    _sendChange();
  }

  void _syncHistory() {
    final canUndo = _quill.hasUndo;
    final canRedo = _quill.hasRedo;
    if (canUndo == _canUndo && canRedo == _canRedo) return;
    _canUndo = canUndo;
    _canRedo = canRedo;
    control.triggerEvent(
        "history_change", {"can_undo": canUndo, "can_redo": canRedo});
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    switch (name) {
      case "undo":
        if (_quill.hasUndo) _quill.undo();
        _publish();
      case "redo":
        if (_quill.hasRedo) _quill.redo();
        _publish();
      case "focus":
        _editorFocus.requestFocus();
      default:
        throw Exception("Unknown NoteEditor method: $name");
    }
  }

  // ── Formatting ────────────────────────────────────────

  /// The word around a collapsed caret, so a format tap behaves like Word.
  TextRange? _wordAtCaret() {
    final selection = _quill.selection;
    if (!selection.isCollapsed) return null;
    final text = _quill.document.toPlainText();
    bool isWord(int i) =>
        i >= 0 && i < text.length && _wordChar.hasMatch(text[i]);
    final offset = selection.baseOffset;
    if (!isWord(offset - 1) || !isWord(offset)) return null;
    var start = offset;
    while (isWord(start - 1)) {
      start--;
    }
    var end = offset;
    while (isWord(end)) {
      end++;
    }
    return TextRange(start: start, end: end);
  }

  /// Applies an inline format to the selection, else the word at the caret,
  /// else to what is typed next.
  void _formatInline(Attribute attribute) {
    final word = _wordAtCaret();
    if (word != null) {
      _quill.formatText(word.start, word.end - word.start, attribute);
    } else {
      _quill.formatSelection(attribute);
    }
    _keepEditing();
  }

  void _toggleInline(Attribute attribute) {
    final active =
        _quill.getSelectionStyle().attributes.containsKey(attribute.key);
    _formatInline(active ? Attribute.clone(attribute, null) : attribute);
  }

  void _setFont(String? family) {
    _formatInline(family == null
        ? Attribute.clone(Attribute.font, null)
        : Attribute.fromKeyValue(Attribute.font.key, family)!);
  }

  void _clearInline() {
    for (final attribute in _inlineKeys) {
      _formatInline(Attribute.clone(attribute, null));
    }
  }

  void _setHeader(int? level) {
    final Attribute attribute =
        level == null ? Attribute.header : HeaderAttribute(level: level);
    _quill.formatSelection(attribute);
    _keepEditing();
  }

  void _toggleList(Attribute attribute, bool active) {
    _quill.formatSelection(
        active ? Attribute.clone(Attribute.list, null) : attribute);
    _keepEditing();
  }

  void _indent(bool increase) {
    _quill.indentSelection(increase);
    _keepEditing();
  }

  void _keepEditing() {
    if (!_editorFocus.hasFocus) _editorFocus.requestFocus();
  }

  void _focusEnd() {
    if (_quill.readOnly) return;
    _quill.moveCursorToEnd();
    _editorFocus.requestFocus();
  }

  // ── Build ─────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final readOnly = control.getBool("read_only", false)!;
    _quill.readOnly = readOnly;
    final colors = _Palette(
      text: control.getColor("text_color", context) ??
          theme.colorScheme.onSurface,
      muted: control.getColor("muted_color", context) ??
          theme.colorScheme.onSurfaceVariant,
      accent: control.getColor("accent_color", context) ??
          theme.colorScheme.primary,
      accentContainer: control.getColor("accent_container_color", context) ??
          theme.colorScheme.primaryContainer,
      bar: control.getColor("toolbar_color", context) ??
          theme.colorScheme.surface,
      divider: control.getColor("divider_color", context) ??
          theme.colorScheme.outlineVariant,
    );
    final header = control.buildWidget("header");

    final title = TextField(
      controller: _title,
      readOnly: readOnly,
      autofocus: control.getBool("autofocus_title", false)!,
      maxLines: null,
      keyboardType: TextInputType.text,
      textInputAction: TextInputAction.next,
      textCapitalization: TextCapitalization.sentences,
      cursorColor: colors.accent,
      style: TextStyle(
          fontSize: 24, fontWeight: FontWeight.w700, color: colors.text),
      decoration: InputDecoration.collapsed(
        hintText: control.getString("title_hint", "Título"),
        hintStyle: TextStyle(
            fontSize: 24, fontWeight: FontWeight.w700, color: colors.muted),
      ),
      onChanged: _onTitleChanged,
      onSubmitted: (_) => _editorFocus.requestFocus(),
    );

    final editor = QuillEditor(
      controller: _quill,
      focusNode: _editorFocus,
      // The page scrolls as a whole (header + title + body); Quill keeps the
      // caret visible through this shared controller.
      scrollController: _scroll,
      config: QuillEditorConfig(
        scrollable: false,
        padding: EdgeInsets.zero,
        placeholder: control.getString("placeholder"),
        textCapitalization: TextCapitalization.sentences,
        customStyles: _styles(colors),
        // ignore: experimental_member_use
        customLeadingBlockBuilder: _listMarker,
        // "- ", "1. ", "# ", "## " turn the line into a list or a heading.
        // ignore: experimental_member_use
        spaceShortcutEvents: standardSpaceShorcutEvents,
      ),
    );

    final body = SingleChildScrollView(
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(24, 4, 24, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (header != null) header,
          const SizedBox(height: 8),
          title,
          const SizedBox(height: 12),
          editor,
          // Tapping the blank space under the text keeps writing at the end.
          GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: _focusEnd,
            child: const SizedBox(height: 240),
          ),
        ],
      ),
    );

    return LayoutControl(
      control: control,
      child: Localizations.override(
        context: context,
        delegates: const [FlutterQuillLocalizations.delegate],
        child: Column(
          children: [
            Expanded(child: body),
            if (!readOnly)
              // Same tap region as the editor: tapping the bar must not
              // unfocus it (that would drop the selection and the keyboard).
              TextFieldTapRegion(child: _buildToolbar(colors)),
          ],
        ),
      ),
    );
  }

  DefaultStyles _styles(_Palette colors) {
    final base = TextStyle(
      fontSize: 16,
      height: 1.45,
      color: colors.text,
      decoration: TextDecoration.none,
    );
    const flat = HorizontalSpacing(0, 0);
    return DefaultStyles(
      paragraph: DefaultTextBlockStyle(
          base, flat, VerticalSpacing.zero, VerticalSpacing.zero, null),
      h1: DefaultTextBlockStyle(
          base.copyWith(fontSize: 26, height: 1.25, fontWeight: FontWeight.w700),
          flat,
          const VerticalSpacing(14, 4),
          VerticalSpacing.zero,
          null),
      h2: DefaultTextBlockStyle(
          base.copyWith(fontSize: 20, height: 1.3, fontWeight: FontWeight.w600),
          flat,
          const VerticalSpacing(10, 2),
          VerticalSpacing.zero,
          null),
      lists: DefaultListBlockStyle(base, flat, const VerticalSpacing(2, 2),
          const VerticalSpacing(0, 4), null, null,
          indentWidthBuilder: _blockIndent),
      // Bullets and numbers are top-aligned with the line, so they need the
      // body's line height or they sit above the text.
      leading: DefaultTextBlockStyle(
          base, flat, VerticalSpacing.zero, VerticalSpacing.zero, null),
      placeHolder: DefaultTextBlockStyle(base.copyWith(color: colors.muted),
          flat, VerticalSpacing.zero, VerticalSpacing.zero, null),
    );
  }

  Widget _buildToolbar(_Palette colors) {
    return ListenableBuilder(
      listenable: _quill,
      builder: (context, _) {
        final attrs = _quill.getSelectionStyle().attributes;
        final headerLevel = attrs[Attribute.header.key]?.value;
        final list = attrs[Attribute.list.key]?.value;
        final font = attrs[Attribute.font.key]?.value as String?;
        bool has(Attribute a) => attrs.containsKey(a.key);
        final isCheck = list == "checked" || list == "unchecked";

        return DecoratedBox(
          decoration: BoxDecoration(
            color: colors.bar,
            border: Border(top: BorderSide(color: colors.divider)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedSize(
                duration: const Duration(milliseconds: 180),
                curve: Curves.easeOutCubic,
                alignment: Alignment.bottomCenter,
                child: _stylePanelOpen
                    ? _buildStylePanel(colors, headerLevel, font)
                    : const SizedBox(width: double.infinity),
              ),
              SizedBox(
                height: 56,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  children: [
                    _ToolButton(
                      tooltip: "Estilo y tipo de letra",
                      width: 60,
                      active: _stylePanelOpen,
                      colors: colors,
                      onTap: () =>
                          setState(() => _stylePanelOpen = !_stylePanelOpen),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text("Aa",
                              style: TextStyle(
                                  fontSize: 17,
                                  fontWeight: FontWeight.w700,
                                  color: colors.text)),
                          Icon(
                              _stylePanelOpen
                                  ? Icons.keyboard_arrow_down_rounded
                                  : Icons.keyboard_arrow_up_rounded,
                              size: 16,
                              color: colors.muted),
                        ],
                      ),
                    ),
                    _separator(colors),
                    _icon(colors, Icons.format_bold_rounded, "Negrita",
                        has(Attribute.bold), () => _toggleInline(Attribute.bold)),
                    _icon(
                        colors,
                        Icons.format_italic_rounded,
                        "Cursiva",
                        has(Attribute.italic),
                        () => _toggleInline(Attribute.italic)),
                    _icon(
                        colors,
                        Icons.format_underlined_rounded,
                        "Subrayado",
                        has(Attribute.underline),
                        () => _toggleInline(Attribute.underline)),
                    _icon(
                        colors,
                        Icons.format_strikethrough_rounded,
                        "Tachado",
                        has(Attribute.strikeThrough),
                        () => _toggleInline(Attribute.strikeThrough)),
                    _separator(colors),
                    _icon(
                        colors,
                        Icons.format_list_bulleted_rounded,
                        "Lista con viñetas",
                        list == "bullet",
                        () => _toggleList(Attribute.ul, list == "bullet")),
                    _icon(
                        colors,
                        Icons.format_list_numbered_rounded,
                        "Lista numerada",
                        list == "ordered",
                        () => _toggleList(Attribute.ol, list == "ordered")),
                    _icon(colors, Icons.checklist_rounded, "Lista de tareas",
                        isCheck, () => _toggleList(Attribute.unchecked, isCheck)),
                    _icon(colors, Icons.format_indent_decrease_rounded,
                        "Reducir sangría", false, () => _indent(false)),
                    _icon(colors, Icons.format_indent_increase_rounded,
                        "Aumentar sangría", false, () => _indent(true)),
                    _separator(colors),
                    _icon(colors, Icons.format_clear_rounded, "Quitar formato",
                        false, _clearInline),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStylePanel(_Palette colors, Object? headerLevel, String? font) {
    Widget styleChip(String label, int? level, double size, FontWeight weight) {
      final active = headerLevel == level;
      return Expanded(
        child: _Chip(
          active: active,
          colors: colors,
          onTap: () => _setHeader(active && level != null ? null : level),
          child: Text(label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                  fontSize: size,
                  fontWeight: weight,
                  color: active ? colors.accent : colors.text)),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              styleChip("Título", 1, 19, FontWeight.w700),
              const SizedBox(width: 8),
              styleChip("Subtítulo", 2, 16, FontWeight.w600),
              const SizedBox(width: 8),
              styleChip("Texto", null, 14, FontWeight.w400),
            ],
          ),
          const SizedBox(height: 8),
          SizedBox(
            height: 64,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: _fonts.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (context, i) {
                final (family, label) = _fonts[i];
                final active = font == family;
                return SizedBox(
                  width: 76,
                  child: _Chip(
                    active: active,
                    colors: colors,
                    onTap: () => _setFont(family),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text("Aa",
                            style: TextStyle(
                                fontFamily: family,
                                fontSize: family == "Caveat" ? 26 : 20,
                                fontWeight: FontWeight.w600,
                                color: colors.text)),
                        Text(label,
                            style: TextStyle(
                                fontSize: 11,
                                fontWeight:
                                    active ? FontWeight.w700 : FontWeight.w500,
                                color: active ? colors.accent : colors.muted)),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _icon(_Palette colors, IconData icon, String tooltip, bool active,
      VoidCallback onTap) {
    return _ToolButton(
      tooltip: tooltip,
      active: active,
      colors: colors,
      onTap: onTap,
      child: Icon(icon, size: 22, color: active ? colors.accent : colors.muted),
    );
  }

  Widget _separator(_Palette colors) => Center(
        child: Container(
          width: 1,
          height: 24,
          margin: const EdgeInsets.symmetric(horizontal: 6),
          color: colors.divider,
        ),
      );
}

class _Palette {
  const _Palette({
    required this.text,
    required this.muted,
    required this.accent,
    required this.accentContainer,
    required this.bar,
    required this.divider,
  });

  final Color text;
  final Color muted;
  final Color accent;
  final Color accentContainer;
  final Color bar;
  final Color divider;
}

class _ToolButton extends StatelessWidget {
  const _ToolButton({
    required this.tooltip,
    required this.active,
    required this.colors,
    required this.onTap,
    required this.child,
    this.width = 44,
  });

  final String tooltip;
  final bool active;
  final _Palette colors;
  final VoidCallback onTap;
  final Widget child;
  final double width;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 1, vertical: 6),
      child: Tooltip(
        message: tooltip,
        child: Material(
          color: active ? colors.accentContainer : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            // Buttons must not steal focus from the editor.
            canRequestFocus: false,
            onTap: onTap,
            child: SizedBox(width: width, child: Center(child: child)),
          ),
        ),
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({
    required this.active,
    required this.colors,
    required this.onTap,
    required this.child,
  });

  final bool active;
  final _Palette colors;
  final VoidCallback onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final shape = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(14),
      side: BorderSide(
        color: active ? colors.accent : colors.divider,
        width: active ? 2 : 1,
      ),
    );
    return Material(
      color: active ? colors.accentContainer : Colors.transparent,
      shape: shape,
      child: InkWell(
        customBorder: shape,
        canRequestFocus: false,
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
          child: Center(child: child),
        ),
      ),
    );
  }
}
