import 'dart:async';
import 'dart:convert';
import 'dart:math' as math;

import 'package:flet/flet.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_quill/flutter_quill.dart';
import 'package:flutter_quill/quill_delta.dart';

part 'ledger.dart';

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

/// [value] kept between [low] and [high] (or [low] when they cross).
double _within(double value, double low, double high) =>
    math.max(low, math.min(value, high));

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
  final _editorKey = GlobalKey<QuillEditorState>();
  final _editorAreaKey = GlobalKey();
  final _viewportKey = GlobalKey();
  String _value = "";
  String _titleValue = "";
  bool _canUndo = false;
  bool _canRedo = false;
  bool _stylePanelOpen = false;
  _Palette? _colors;

  /// Where the caret was last seen, to tell which way it was moving.
  int _lastCaret = 0;

  /// The table being dragged by its handle, if any.
  _TableDrag? _drag;

  /// The y (in the editor area) of the line where a dragged table would
  /// land; null hides it.
  final _dropLine = ValueNotifier<double?>(null);

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
    _quill.addListener(_keepCaretOffTables);
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
    _drag?.ticker.cancel();
    _quill.removeListener(_syncHistory);
    _quill.removeListener(_keepCaretOffTables);
    _quill.dispose();
    _editorFocus.dispose();
    _scroll.dispose();
    _title.dispose();
    _dropLine.dispose();
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
        _undo();
      case "redo":
        _redo();
      case "focus":
        _editorFocus.requestFocus();
      default:
        throw Exception("Unknown NoteEditor method: $name");
    }
  }

  void _undo() {
    if (_quill.hasUndo) _quill.undo();
    _publish();
  }

  void _redo() {
    if (_quill.hasRedo) _quill.redo();
    _publish();
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

  // ── Dated table ───────────────────────────────────────

  /// Puts a new table on its own line at the caret and opens it.
  void _insertLedger() {
    final selection = _quill.selection;
    if (!selection.isCollapsed) {
      _quill.replaceText(
          selection.start, selection.end - selection.start, '', null);
    }
    final plain = _quill.document.toPlainText();
    final start = _quill.selection.start;
    final index = start < 0 ? 0 : (start >= plain.length ? plain.length - 1 : start);
    final line = _quill.document.queryChild(index).node;
    final lineAttrs = line?.style.toJson() ?? const <String, dynamic>{};
    final splitBefore = index > 0 && plain[index - 1] != '\n';
    final atLineEnd = plain[index] == '\n';
    final lastLine = index == plain.length - 1;

    // Quill only lays out a block embed on its own when it is alone on its
    // line, and only adds those line breaks for videos, so do it here.
    final at = splitBefore ? index + 1 : index;
    final data = _LedgerData();
    final delta = Delta()..retain(index);
    if (splitBefore) {
      delta.insert('\n', lineAttrs.isEmpty ? null : Map.of(lineAttrs));
    }
    delta.insert(BlockEmbed(_ledgerType, data.encode()).toJson());
    if (!atLineEnd || lastLine) {
      // A fresh plain line; at the end it also leaves room to keep writing.
      delta.insert('\n');
    } else if (lineAttrs.isNotEmpty) {
      // Reusing an empty list item or heading: drop its block format.
      delta.retain(1, {for (final key in lineAttrs.keys) key: null});
    }
    _quill.compose(
        delta, TextSelection.collapsed(offset: at + 2), ChangeSource.local);
    _editLedger(at, data, isNew: true);
  }

  void _openLedger(Embed node) {
    final offset = node.documentOffset;
    final data = _LedgerData.decode(node.value.data);
    // The editor handles the same tap (caret, keyboard); open afterwards.
    Timer.run(() {
      if (mounted) _editLedger(offset, data);
    });
  }

  /// The stored JSON of the table at [offset], if it is still there.
  String? _ledgerAt(int offset) {
    var position = 0;
    for (final op in _quill.document.toDelta().toList()) {
      if (position == offset) {
        final data = op.data;
        if (data is Map && data[_ledgerType] is String) {
          return data[_ledgerType] as String;
        }
        return null;
      }
      position += op.length ?? 0;
      if (position > offset) return null;
    }
    return null;
  }

  Future<void> _editLedger(int offset, _LedgerData data,
      {bool isNew = false}) async {
    final colors = _colors;
    if (colors == null) return;
    _editorFocus.unfocus();
    final draft = data.copy();
    final delete = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      showDragHandle: true,
      backgroundColor: colors.bar,
      builder: (_) => _LedgerSheet(draft: draft, colors: colors, isNew: isNew),
    );
    if (!mounted) return;
    final stored = _ledgerAt(offset);
    if (stored == null) return;
    if (delete == true) {
      // Its line break goes too, unless it is the document's last one.
      final count = offset + 1 < _quill.document.length - 1 ? 2 : 1;
      _quill.compose(Delta()..retain(offset)..delete(count),
          TextSelection.collapsed(offset: offset), ChangeSource.local);
      return;
    }
    final encoded = draft.compact().encode();
    if (encoded == stored) return;
    _quill.compose(
        Delta()
          ..retain(offset)
          ..delete(1)
          ..insert(BlockEmbed(_ledgerType, encoded).toJson()),
        _quill.selection,
        ChangeSource.local);
  }

  /// The line holding a table, if [offset] falls on one.
  Line? _tableLine(int offset) {
    if (offset < 0 || offset >= _quill.document.length) return null;
    final node = _quill.document.queryChild(offset).node;
    if (node is! Line || node.childCount != 1) return null;
    final leaf = node.first;
    return leaf is Embed && leaf.value.type == _ledgerType ? node : null;
  }

  /// A table fills its whole line, so a caret beside it is drawn as tall as
  /// the table, a big bar at its left or right edge. Undo and redo put the
  /// caret there, and so do the arrow keys or a tap. Move it to the line
  /// below the table, or the one above when the caret was moving up or the
  /// table is the last line.
  void _keepCaretOffTables() {
    final selection = _quill.selection;
    if (!selection.isCollapsed || selection.baseOffset < 0) return;
    final offset = selection.baseOffset;
    final line = _tableLine(offset);
    if (line == null) {
      _lastCaret = offset;
      return;
    }
    final start = line.documentOffset;
    final below = start + line.length;
    final hasBelow = below < _quill.document.length;
    final hasAbove = start > 0;
    final int target;
    if (hasAbove && (offset < _lastCaret || !hasBelow)) {
      target = start - 1;
    } else if (hasBelow) {
      target = below;
    } else {
      return;
    }
    _lastCaret = target;
    _quill.updateSelection(
        TextSelection.collapsed(offset: target), ChangeSource.silent);
  }

  // ── Moving a table ────────────────────────────────────

  RenderEditor? get _renderEditor =>
      _editorKey.currentState?.editableTextKey.currentState?.renderEditor;

  void _onTableDragStart(Embed node) {
    _drag?.ticker.cancel();
    HapticFeedback.selectionClick();
    _drag = _TableDrag(
      node,
      // Scrolls the note while the table is held near its top or bottom.
      Timer.periodic(const Duration(milliseconds: 16), (_) => _autoScroll()),
    );
  }

  void _onTableDragUpdate(Offset pointer) {
    final drag = _drag;
    if (drag == null) return;
    drag.pointer = pointer;
    _updateDropSlot();
  }

  void _onTableDragEnd() {
    final drag = _stopTableDrag();
    final slot = drag?.slot;
    if (drag == null || slot == null) return;
    final from = drag.node.documentOffset;
    if (_tableLine(from) == null) return;
    HapticFeedback.lightImpact();
    _moveLedger(from, slot);
  }

  /// Ends the drag without moving anything (the table went away mid-drag).
  void _onTableDragCancel() {
    _stopTableDrag(notify: false);
    // Called while the tree is being torn down; hide the line afterwards.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted && _drag == null) _dropLine.value = null;
    });
  }

  _TableDrag? _stopTableDrag({bool notify = true}) {
    final drag = _drag;
    drag?.ticker.cancel();
    _drag = null;
    if (notify) _dropLine.value = null;
    return drag;
  }

  /// Finds the line break nearest the pointer: before or after the line
  /// under it. Shows the drop line there unless the table would not move.
  void _updateDropSlot() {
    final drag = _drag;
    final pointer = drag?.pointer;
    final editor = _renderEditor;
    final area = _editorAreaKey.currentContext?.findRenderObject();
    if (drag == null ||
        pointer == null ||
        editor == null ||
        !editor.hasSize ||
        area is! RenderBox) {
      return;
    }
    final local = editor.globalToLocal(pointer);
    final size = editor.size;
    // Above or below the text counts as the first or last line.
    final probe = Offset(
      _within(local.dx, 1, size.width - 1),
      _within(local.dy, 1, size.height - 1),
    );
    final document = _quill.document;
    final position = editor.getPositionForOffset(editor.localToGlobal(probe));
    final index = math.max(0, math.min(position.offset, document.length - 1));
    final node = document.queryChild(index).node;
    if (node is! Line) return;
    final start = node.documentOffset;
    final end = start + node.length;
    final top = editor.getLocalRectForCaret(TextPosition(offset: start)).top;
    final bottom =
        editor.getLocalRectForCaret(TextPosition(offset: end - 1)).bottom;
    final before = local.dy < (top + bottom) / 2;
    final slot = before ? start : end;
    final from = drag.node.documentOffset;
    // Right above or right below the table itself: it would stay put.
    if (slot == from || slot == from + 2) {
      drag.slot = null;
      _dropLine.value = null;
      return;
    }
    drag.slot = slot;
    final y = before ? top : bottom;
    _dropLine.value = area.globalToLocal(editor.localToGlobal(Offset(0, y))).dy;
  }

  void _autoScroll() {
    final pointer = _drag?.pointer;
    final viewport = _viewportKey.currentContext?.findRenderObject();
    if (pointer == null || viewport is! RenderBox || !_scroll.hasClients) {
      return;
    }
    const edge = 72.0;
    const maxStep = 16.0;
    final top = viewport.localToGlobal(Offset.zero).dy;
    final bottom = top + viewport.size.height;
    double step = 0;
    if (pointer.dy < top + edge) {
      step = -maxStep * _within((top + edge - pointer.dy) / edge, 0, 1);
    } else if (pointer.dy > bottom - edge) {
      step = maxStep * _within((pointer.dy - bottom + edge) / edge, 0, 1);
    }
    if (step == 0) return;
    final position = _scroll.position;
    final target = _within(position.pixels + step, position.minScrollExtent,
        position.maxScrollExtent);
    if (target == position.pixels) return;
    _scroll.jumpTo(target);
    _updateDropSlot();
  }

  /// Moves the table at [from] to the line break [to] (an offset in the
  /// document as it is now), in one step that undo reverts at once.
  void _moveLedger(int from, int to) {
    final stored = _ledgerAt(from);
    if (stored == null) return;
    final document = _quill.document;
    final length = document.length;
    // Its line break goes too, unless it is the document's last one.
    final count = from + 2 < length ? 2 : 1;
    final remaining = length - count;
    var at = to > from ? to - count : to;
    final last = document.queryChild(length - 1).node;
    final lastAttrs = count == 2 && last is Line
        ? (last.style.toJson() ?? const <String, dynamic>{})
        : const <String, dynamic>{};
    final lastIsEmpty = count == 1 || (last is Line && last.length == 1);
    final embed = BlockEmbed(_ledgerType, stored).toJson();

    final insert = Delta();
    final int table;
    if (at >= remaining && !lastIsEmpty) {
      // Below the last line: end that line, then the table and an empty
      // line to keep writing on.
      insert
        ..retain(remaining - 1)
        ..insert('\n', lastAttrs.isEmpty ? null : Map.of(lastAttrs))
        ..insert(embed)
        ..insert('\n');
      if (lastAttrs.isNotEmpty) {
        insert.retain(1, {for (final key in lastAttrs.keys) key: null});
      }
      table = remaining;
    } else {
      // At the start of a line; at the very end, above the empty last line.
      if (at >= remaining) at = remaining - 1;
      insert
        ..retain(at)
        ..insert(embed)
        ..insert('\n');
      table = at;
    }
    final delta = (Delta()
          ..retain(from)
          ..delete(count))
        .compose(insert);
    _quill.compose(
        delta, TextSelection.collapsed(offset: table + 2), ChangeSource.local);
  }

  void _focusEnd() {
    if (_quill.readOnly) return;
    final end = _quill.document.length - 1;
    if (_tableLine(end) != null) {
      // A table ends the note: open a line under it to write on.
      _quill.compose(
          Delta()
            ..retain(end)
            ..insert('\n'),
          TextSelection.collapsed(offset: end + 1),
          ChangeSource.local);
    } else {
      _quill.moveCursorToEnd();
    }
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
    _colors = colors;
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
      key: _editorKey,
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
        embedBuilders: [
          _LedgerEmbedBuilder(
            colors: colors,
            onOpen: _openLedger,
            onDragStart: _onTableDragStart,
            onDragUpdate: _onTableDragUpdate,
            onDragEnd: _onTableDragEnd,
            onDragCancel: _onTableDragCancel,
          ),
        ],
        // ignore: experimental_member_use
        customLeadingBlockBuilder: _listMarker,
        // "- ", "1. ", "# ", "## " turn the line into a list or a heading.
        // ignore: experimental_member_use
        spaceShortcutEvents: standardSpaceShorcutEvents,
      ),
    );

    // The editor plus the line that shows where a dragged table will land.
    final editorArea = Stack(
      key: _editorAreaKey,
      clipBehavior: Clip.none,
      children: [
        editor,
        ValueListenableBuilder<double?>(
          valueListenable: _dropLine,
          builder: (context, y, _) => y == null
              ? const SizedBox.shrink()
              : Positioned(
                  left: -6,
                  right: 0,
                  top: y - 5,
                  child: IgnorePointer(child: _DropLine(color: colors.accent)),
                ),
        ),
      ],
    );

    final body = SingleChildScrollView(
      key: _viewportKey,
      controller: _scroll,
      padding: const EdgeInsets.fromLTRB(24, 4, 24, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (header != null) header,
          const SizedBox(height: 8),
          title,
          const SizedBox(height: 12),
          editorArea,
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
              // Undo far left, redo far right, on a row of their own so they
              // never sit among the formatting buttons or over the text.
              SizedBox(
                height: 44,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      _HistoryButton(
                        icon: Icons.undo_rounded,
                        label: "Deshacer",
                        enabled: _quill.hasUndo,
                        colors: colors,
                        onTap: _undo,
                      ),
                      _HistoryButton(
                        icon: Icons.redo_rounded,
                        label: "Rehacer",
                        enabled: _quill.hasRedo,
                        colors: colors,
                        onTap: _redo,
                        iconAfter: true,
                      ),
                    ],
                  ),
                ),
              ),
              Divider(height: 1, thickness: 1, color: colors.divider),
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
                    _icon(colors, Icons.table_chart_outlined,
                        "Tabla con fecha", false, _insertLedger),
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

/// A table being moved by its handle.
class _TableDrag {
  _TableDrag(this.node, this.ticker);

  final Embed node;
  final Timer ticker;

  /// Where the finger (or mouse) is, in global coordinates.
  Offset? pointer;

  /// The line break the table would move to; null leaves it where it is.
  int? slot;
}

/// A dot and a bar across the note where a dragged table will land.
class _DropLine extends StatelessWidget {
  const _DropLine({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 10,
      child: Row(
        children: [
          Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: color, width: 2.5),
            ),
          ),
          Expanded(
            child: Container(
              height: 3,
              decoration: BoxDecoration(
                color: color,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
        ],
      ),
    );
  }
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

class _HistoryButton extends StatelessWidget {
  const _HistoryButton({
    required this.icon,
    required this.label,
    required this.enabled,
    required this.colors,
    required this.onTap,
    this.iconAfter = false,
  });

  final IconData icon;
  final String label;
  final bool enabled;
  final _Palette colors;
  final VoidCallback onTap;
  final bool iconAfter;

  @override
  Widget build(BuildContext context) {
    final color = enabled ? colors.text : colors.muted.withValues(alpha: 0.55);
    final parts = [
      Icon(icon, size: 20, color: color),
      const SizedBox(width: 6),
      Text(label,
          style: TextStyle(
              fontSize: 14, fontWeight: FontWeight.w600, color: color)),
    ];
    return Material(
      color: Colors.transparent,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        // Buttons must not steal focus from the editor.
        canRequestFocus: false,
        onTap: enabled ? onTap : null,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: iconAfter ? parts.reversed.toList() : parts,
          ),
        ),
      ),
    );
  }
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
