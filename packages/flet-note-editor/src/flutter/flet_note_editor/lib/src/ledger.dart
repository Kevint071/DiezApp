part of 'note_editor.dart';

// ── Dated table ────────────────────────────────────────
//
// A block embed of type "ledger": a merged header cell with a date, then
// "Descripción | Valor" rows and the total of the values in the last row.
// More dates can split the rows: a date row spans both columns like the
// header, and the total still adds up every value in the table.
// The Delta stores it as {"insert": {"ledger": "<json>"}} with
// {"date": "15/11/2026", "rows": [{"description": "...", "value": "..."},
//  {"date": "16/11/2026"}, ...]}.
//
// Values keep the typed text. Dots group thousands and a comma starts the
// decimals, like the calculator. The Python side
// (features/notes/domain/note_table.py) parses them with the same rules.

const _ledgerType = 'ledger';

class _LedgerRow {
  _LedgerRow([this.description = '', this.value = '']) : date = null;

  /// A date that separates the rows below it from the ones above.
  _LedgerRow.date(String this.date)
      : description = '',
        value = '';

  String description;
  String value;
  String? date;

  bool get isDate => date != null;

  bool get isBlank => isDate
      ? date!.trim().isEmpty
      : description.trim().isEmpty && value.trim().isEmpty;

  _LedgerRow copy({bool trim = false}) {
    String clean(String s) => trim ? s.trim() : s;
    return isDate
        ? _LedgerRow.date(clean(date!))
        : _LedgerRow(clean(description), clean(value));
  }

  Map<String, String> toJson() => isDate
      ? {'date': date!}
      : {'description': description, 'value': value};
}

class _LedgerData {
  _LedgerData({this.date = '', List<_LedgerRow>? rows}) : rows = rows ?? [];

  String date;
  List<_LedgerRow> rows;

  factory _LedgerData.decode(Object? raw) {
    try {
      final json = raw is String ? jsonDecode(raw) : raw;
      if (json is! Map) return _LedgerData();
      final rows = <_LedgerRow>[
        for (final row in (json['rows'] as List? ?? const []))
          if (row is Map && row.containsKey('date'))
            _LedgerRow.date('${row['date'] ?? ''}')
          else if (row is Map)
            _LedgerRow('${row['description'] ?? ''}', '${row['value'] ?? ''}'),
      ];
      return _LedgerData(date: '${json['date'] ?? ''}', rows: rows);
    } catch (e) {
      debugPrint("NoteEditor: invalid table ($e)");
      return _LedgerData();
    }
  }

  String encode() => jsonEncode({
        'date': date,
        'rows': [for (final row in rows) row.toJson()],
      });

  _LedgerData copy() => _LedgerData(
        date: date,
        rows: [for (final row in rows) row.copy()],
      );

  /// Trimmed, without the rows left completely empty.
  _LedgerData compact() => _LedgerData(
        date: date.trim(),
        rows: [
          for (final row in rows)
            if (!row.isBlank) row.copy(trim: true),
        ],
      );

  int get totalCents => rows.fold(
      0, (sum, row) => sum + (row.isDate ? 0 : _parseCents(row.value) ?? 0));
}

final _digitsOnly = RegExp(r'^\d*$');

/// "1.234,5" → 123450; null when blank or not a number.
int? _parseCents(String text) {
  var s = text.replaceAll(RegExp(r'\s'), '').replaceAll(r'$', '');
  s = s.replaceAll('.', '');
  final negative = s.startsWith('-');
  if (negative) s = s.substring(1);
  final comma = s.indexOf(',');
  final whole = comma < 0 ? s : s.substring(0, comma);
  final frac = comma < 0 ? '' : s.substring(comma + 1);
  if (whole.isEmpty && frac.isEmpty) return null;
  if (!_digitsOnly.hasMatch(whole) ||
      !_digitsOnly.hasMatch(frac) ||
      frac.length > 2) {
    return null;
  }
  final units = int.tryParse(whole.isEmpty ? '0' : whole);
  if (units == null) return null;
  final cents = units * 100 + int.parse(frac.padRight(2, '0'));
  return negative ? -cents : cents;
}

/// 123450 → "$1.234,50"; whole amounts drop the decimals.
String _formatCents(int cents) {
  final sign = cents < 0 ? '-' : '';
  final abs = cents.abs();
  final frac = abs % 100;
  final decimals = frac == 0 ? '' : ',${frac.toString().padLeft(2, '0')}';
  return '$sign\$${_group('${abs ~/ 100}')}$decimals';
}

/// "1234567" → "1.234.567".
String _group(String digits) {
  final out = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) out.write('.');
    out.write(digits[i]);
  }
  return out.toString();
}

String _twoDigits(int n) => n.toString().padLeft(2, '0');

/// Keeps a value as "-1.234,56" while typing: dots are added for thousands,
/// a comma starts up to two decimals.
class _AmountFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
      TextEditingValue oldValue, TextEditingValue newValue) {
    final raw = newValue.text;
    final negative = raw.trimLeft().startsWith('-');
    final kept = raw.replaceAll(RegExp(r'[^0-9,]'), '');
    final comma = kept.indexOf(',');
    var whole = comma < 0 ? kept : kept.substring(0, comma);
    var frac = comma < 0 ? null : kept.substring(comma + 1).replaceAll(',', '');
    if (frac != null && frac.length > 2) frac = frac.substring(0, 2);
    whole = whole.replaceFirst(RegExp(r'^0+(?=\d)'), '');
    if (whole.isEmpty && frac != null) whole = '0';
    final text =
        '${negative ? '-' : ''}${_group(whole)}${frac == null ? '' : ',$frac'}';
    return TextEditingValue(
        text: text, selection: TextSelection.collapsed(offset: text.length));
  }
}

/// Keeps a date as "dd/mm/aaaa" while typing.
class _DateFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
      TextEditingValue oldValue, TextEditingValue newValue) {
    final erasing = newValue.text.length < oldValue.text.length;
    var digits = newValue.text.replaceAll(RegExp(r'\D'), '');
    if (digits.length > 8) digits = digits.substring(0, 8);
    final out = StringBuffer();
    for (var i = 0; i < digits.length; i++) {
      if (i == 2 || i == 4) out.write('/');
      out.write(digits[i]);
    }
    // The slash shows up as soon as the day or month is complete.
    if (!erasing && (digits.length == 2 || digits.length == 4)) out.write('/');
    final text = out.toString();
    return TextEditingValue(
        text: text, selection: TextSelection.collapsed(offset: text.length));
  }
}

class _LedgerEmbedBuilder extends EmbedBuilder {
  const _LedgerEmbedBuilder({
    required this.colors,
    required this.onOpen,
    required this.onDragStart,
    required this.onDragUpdate,
    required this.onDragEnd,
    required this.onDragCancel,
  });

  final _Palette colors;
  final void Function(Embed node) onOpen;
  final void Function(Embed node) onDragStart;
  final void Function(Offset pointer) onDragUpdate;
  final VoidCallback onDragEnd;
  final VoidCallback onDragCancel;

  @override
  String get key => _ledgerType;

  @override
  Widget build(BuildContext context, EmbedContext embedContext) {
    final node = embedContext.node;
    final editable = !embedContext.readOnly;
    return _LedgerView(
      data: _LedgerData.decode(node.value.data),
      colors: colors,
      onTap: editable ? () => onOpen(node) : null,
      drag: editable
          ? _LedgerDragCallbacks(
              start: () => onDragStart(node),
              update: onDragUpdate,
              end: onDragEnd,
              cancel: onDragCancel,
            )
          : null,
    );
  }
}

class _LedgerDragCallbacks {
  const _LedgerDragCallbacks({
    required this.start,
    required this.update,
    required this.end,
    required this.cancel,
  });

  final VoidCallback start;
  final void Function(Offset pointer) update;
  final VoidCallback end;
  final VoidCallback cancel;
}

/// The table as it sits in the note. Tapping it opens [_LedgerSheet]; the
/// six dots in its top-left corner drag it to another line of the note.
class _LedgerView extends StatefulWidget {
  const _LedgerView({
    required this.data,
    required this.colors,
    this.onTap,
    this.drag,
  });

  final _LedgerData data;
  final _Palette colors;
  final VoidCallback? onTap;
  final _LedgerDragCallbacks? drag;

  @override
  State<_LedgerView> createState() => _LedgerViewState();
}

class _LedgerViewState extends State<_LedgerView> {
  final _tableKey = GlobalKey();
  bool _dragging = false;

  /// The table's width when the drag started, for the copy that follows.
  double _width = 0;

  @override
  void dispose() {
    // Draggable skips onDragEnd once its widget is gone.
    if (_dragging) widget.drag?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final drag = widget.drag;
    final table = _LedgerTable(
      key: _tableKey,
      data: widget.data,
      colors: widget.colors,
      handle: drag == null ? null : _handle(drag),
      hint: widget.onTap == null ? 'Sin filas' : 'Toca para agregar filas',
    );
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: widget.onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: AnimatedOpacity(
          opacity: _dragging ? 0.35 : 1,
          duration: const Duration(milliseconds: 120),
          child: table,
        ),
      ),
    );
  }

  Widget _handle(_LedgerDragCallbacks drag) {
    final colors = widget.colors;
    final dots = _LedgerHandle(colors: colors);
    // The copy that follows the finger: the same table, lifted off the
    // page. Very tall tables are cut off at the bottom. Built once the drag
    // has started, so _width is known by then.
    final feedback = Builder(
      builder: (context) => SizedBox(
        width: _width,
        child: Material(
          color: colors.bar,
          elevation: 10,
          shadowColor: Colors.black54,
          borderRadius: BorderRadius.circular(12),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 280),
            child: SingleChildScrollView(
              primary: false,
              physics: const NeverScrollableScrollPhysics(),
              child: _LedgerTable(
                data: widget.data,
                colors: colors,
                handle: dots,
                hint: '',
              ),
            ),
          ),
        ),
      ),
    );
    return MouseRegion(
      cursor: SystemMouseCursors.grab,
      child: _GrabDraggable(
        // The copy starts exactly over the table, its handle under the
        // finger, and follows it from there.
        dragAnchorStrategy: childDragAnchorStrategy,
        feedback: feedback,
        onDragStarted: () {
          final box = _tableKey.currentContext?.findRenderObject();
          setState(() {
            _width = box is RenderBox && box.hasSize ? box.size.width : 320;
            _dragging = true;
          });
          drag.start();
        },
        onDragUpdate: (details) => drag.update(details.globalPosition),
        onDragEnd: (_) {
          setState(() => _dragging = false);
          drag.end();
        },
        child: dots,
      ),
    );
  }
}

/// A [Draggable] that takes the pointer as soon as it lands, so the
/// editor's tap and long-press (text selection) and the page's scroll never
/// get it: holding the handle still before moving still drags the table.
class _GrabDraggable extends Draggable<Object> {
  const _GrabDraggable({
    required super.child,
    required super.feedback,
    super.dragAnchorStrategy,
    super.onDragStarted,
    super.onDragUpdate,
    super.onDragEnd,
  });

  @override
  MultiDragGestureRecognizer createRecognizer(
          GestureMultiDragStartCallback onStart) =>
      _GrabRecognizer()..onStart = onStart;
}

class _GrabRecognizer extends MultiDragGestureRecognizer {
  _GrabRecognizer() : super(debugOwner: null);

  _GrabPointerState? _arrived;

  @override
  MultiDragPointerState createNewPointerState(PointerDownEvent event) =>
      _arrived = _GrabPointerState(event.position, event.kind, gestureSettings);

  @override
  void addAllowedPointer(PointerDownEvent event) {
    super.addAllowedPointer(event);
    // Its arena entry exists now: win it before anyone else can.
    _arrived?.claim();
    _arrived = null;
  }

  @override
  String get debugDescription => 'table grab';
}

class _GrabPointerState extends MultiDragPointerState {
  _GrabPointerState(super.initialPosition, super.kind, super.gestureSettings);

  void claim() => resolve(GestureDisposition.accepted);

  @override
  void accepted(GestureMultiDragStartCallback starter) {
    starter(initialPosition);
  }
}

/// The six dots that grab a table, in the corner of its date header.
class _LedgerHandle extends StatelessWidget {
  const _LedgerHandle({required this.colors});

  final _Palette colors;

  @override
  Widget build(BuildContext context) {
    // Opaque to hits, so the whole corner grabs and not only the dots.
    return ColoredBox(
      color: Colors.transparent,
      child: SizedBox(
        width: 44,
        height: 42,
        child: Center(
          child: Icon(
            Icons.drag_indicator_rounded,
            size: 22,
            color: colors.accent.withValues(alpha: 0.85),
          ),
        ),
      ),
    );
  }
}

/// The bordered table itself, as drawn in the note and while dragged.
class _LedgerTable extends StatelessWidget {
  const _LedgerTable({
    super.key,
    required this.data,
    required this.colors,
    required this.hint,
    this.handle,
  });

  final _LedgerData data;
  final _Palette colors;

  /// What the row says when the table has no rows yet.
  final String hint;

  /// Sits in the top-left corner of the date header.
  final Widget? handle;

  @override
  Widget build(BuildContext context) {
    final error = Theme.of(context).colorScheme.error;
    final line = BorderSide(color: colors.divider);
    final base = TextStyle(fontSize: 15, height: 1.3, color: colors.text);
    final label = base.copyWith(
        fontSize: 13, fontWeight: FontWeight.w600, color: colors.muted);
    final strong = base.copyWith(fontWeight: FontWeight.w700);

    Widget cell(String text, TextStyle style, {bool end = false}) => Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          child: Text(text,
              style: style, textAlign: end ? TextAlign.end : TextAlign.start),
        );

    // Flutter's Table cannot merge cells, so rows are built by hand.
    Widget pair(Widget left, Widget right, {Color? color}) => Container(
          color: color,
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(flex: 3, child: left),
                VerticalDivider(width: 1, thickness: 1, color: colors.divider),
                Expanded(flex: 2, child: right),
              ],
            ),
          ),
        );

    // A cell across both columns: the header and each date separator.
    Widget dateCell(String date) {
      final value = date.trim();
      return Container(
        color: colors.accentContainer,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.event_rounded, size: 18, color: colors.accent),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                value.isEmpty ? 'dd/mm/aaaa' : value,
                style: value.isEmpty ? base.copyWith(color: colors.muted) : strong,
              ),
            ),
          ],
        ),
      );
    }

    final rule = Divider(height: 1, thickness: 1, color: colors.divider);
    final handle = this.handle;
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        border: Border.fromBorderSide(line),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (handle == null)
            dateCell(data.date)
          else
            Stack(
              children: [
                dateCell(data.date),
                Positioned(left: 0, top: 0, bottom: 0, child: handle),
              ],
            ),
          rule,
          pair(cell('Descripción', label), cell('Valor', label, end: true)),
          for (final row in data.rows) ...[
            rule,
            if (row.isDate)
              dateCell(row.date!)
            else
              pair(
                cell(row.description, base),
                cell(
                  row.value,
                  row.value.trim().isNotEmpty && _parseCents(row.value) == null
                      ? base.copyWith(color: error)
                      : base,
                  end: true,
                ),
              ),
          ],
          if (data.rows.isEmpty) ...[
            rule,
            pair(
              cell(hint, base.copyWith(color: colors.muted)),
              cell('', base),
            ),
          ],
          rule,
          pair(
            cell('Total', strong),
            cell(_formatCents(data.totalCents), strong, end: true),
            color: colors.accentContainer.withValues(alpha: 0.45),
          ),
        ],
      ),
    );
  }
}

/// Edits a table in a bottom sheet. Pops `true` to delete it; any other way
/// out keeps what was typed (it is written into [draft] as it changes).
class _LedgerSheet extends StatefulWidget {
  const _LedgerSheet({
    required this.draft,
    required this.colors,
    required this.isNew,
  });

  final _LedgerData draft;
  final _Palette colors;
  final bool isNew;

  @override
  State<_LedgerSheet> createState() => _LedgerSheetState();
}

/// The text fields of one row of the sheet: a description and a value, or
/// a date that separates rows ([date] is set only then).
class _RowFields {
  _RowFields(_LedgerRow row)
      : date = row.isDate ? TextEditingController(text: row.date) : null,
        description = TextEditingController(text: row.description),
        value = TextEditingController(text: row.value);

  final TextEditingController? date;
  final TextEditingController description;
  final TextEditingController value;

  bool get isDate => date != null;

  _LedgerRow toRow() => isDate
      ? _LedgerRow.date(date!.text)
      : _LedgerRow(description.text, value.text);

  void dispose() {
    date?.dispose();
    description.dispose();
    value.dispose();
  }
}

class _LedgerSheetState extends State<_LedgerSheet> {
  late final TextEditingController _date;
  final List<_RowFields> _rows = [];
  _RowFields? _added;

  _LedgerData get _draft => widget.draft;

  @override
  void initState() {
    super.initState();
    _date = TextEditingController(text: _draft.date);
    _rows.addAll(_draft.rows.map(_RowFields.new));
    if (_rows.isEmpty) _rows.add(_RowFields(_LedgerRow()));
    _sync();
  }

  @override
  void dispose() {
    _date.dispose();
    for (final row in _rows) {
      row.dispose();
    }
    super.dispose();
  }

  void _sync() {
    _draft
      ..date = _date.text
      ..rows = [for (final row in _rows) row.toRow()];
  }

  void _changed() => setState(_sync);

  void _today(TextEditingController field) {
    final now = DateTime.now();
    field.text = '${_twoDigits(now.day)}/${_twoDigits(now.month)}/${now.year}';
    _changed();
  }

  void _addRow() {
    final row = _RowFields(_LedgerRow());
    _rows.add(row);
    _added = row;
    _changed();
  }

  /// A date separator plus an empty row to write under it.
  void _addDate() {
    final separator = _RowFields(_LedgerRow.date(''));
    _rows
      ..add(separator)
      ..add(_RowFields(_LedgerRow()));
    _added = separator;
    _changed();
  }

  void _removeRow(_RowFields row) {
    _rows.remove(row);
    if (_rows.isEmpty) _rows.add(_RowFields(_LedgerRow()));
    _changed();
    // The fields may still be in this frame's tree.
    WidgetsBinding.instance.addPostFrameCallback((_) => row.dispose());
  }

  InputDecoration _decoration(String hint, {Widget? suffix}) {
    final c = widget.colors;
    OutlineInputBorder border(Color color, double width) => OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: color, width: width),
        );
    return InputDecoration(
      isDense: true,
      hintText: hint,
      hintStyle: TextStyle(color: c.muted),
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      border: border(c.divider, 1),
      enabledBorder: border(c.divider, 1),
      focusedBorder: border(c.accent, 2),
      suffixIcon: suffix,
    );
  }

  Widget _dateField(TextEditingController field, {bool autofocus = false}) {
    final c = widget.colors;
    return TextField(
      controller: field,
      autofocus: autofocus,
      keyboardType: TextInputType.number,
      inputFormatters: [_DateFormatter()],
      textAlign: TextAlign.center,
      cursorColor: c.accent,
      style: TextStyle(fontSize: 15, color: c.text, fontWeight: FontWeight.w700),
      decoration: _decoration(
        'dd/mm/aaaa',
        suffix: TextButton(
          onPressed: () => _today(field),
          style: TextButton.styleFrom(foregroundColor: c.accent),
          child: const Text('Hoy'),
        ),
      ),
      onChanged: (_) => _changed(),
    );
  }

  Widget _removeButton(_RowFields row, String tooltip) => SizedBox(
        width: 40,
        child: IconButton(
          tooltip: tooltip,
          icon: Icon(Icons.close_rounded, size: 20, color: widget.colors.muted),
          onPressed: () => _removeRow(row),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final c = widget.colors;
    final scheme = Theme.of(context).colorScheme;
    final text = TextStyle(fontSize: 15, color: c.text);
    // Column titles in the text colour; only the placeholders stay muted.
    final label =
        TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: c.text);

    Widget valueRow(_RowFields row) => Row(
          children: [
            Expanded(
              flex: 3,
              child: TextField(
                controller: row.description,
                autofocus: identical(row, _added),
                textCapitalization: TextCapitalization.sentences,
                textInputAction: TextInputAction.next,
                cursorColor: c.accent,
                style: text,
                decoration: _decoration('Descripción'),
                onChanged: (_) => _changed(),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              flex: 2,
              child: TextField(
                controller: row.value,
                keyboardType: const TextInputType.numberWithOptions(
                    signed: true, decimal: true),
                inputFormatters: [_AmountFormatter()],
                textAlign: TextAlign.end,
                cursorColor: c.accent,
                style: text,
                decoration: _decoration('0'),
                onChanged: (_) => _changed(),
              ),
            ),
            _removeButton(row, 'Quitar fila'),
          ],
        );

    Widget dateRow(_RowFields row) => Row(
          children: [
            Expanded(
              child: _dateField(row.date!, autofocus: identical(row, _added)),
            ),
            _removeButton(row, 'Quitar fecha'),
          ],
        );

    final fields = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _dateField(_date, autofocus: widget.isNew),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(flex: 3, child: Text('Descripción', style: label)),
            const SizedBox(width: 8),
            Expanded(
                flex: 2,
                child: Text('Valor', style: label, textAlign: TextAlign.end)),
            const SizedBox(width: 40),
          ],
        ),
        for (final row in _rows)
          Padding(
            key: ObjectKey(row),
            padding: EdgeInsets.only(top: row.isDate ? 16 : 8),
            child: row.isDate ? dateRow(row) : valueRow(row),
          ),
        Wrap(
          spacing: 4,
          children: [
            TextButton.icon(
              onPressed: _addRow,
              style: TextButton.styleFrom(foregroundColor: c.accent),
              icon: const Icon(Icons.add_rounded),
              label: const Text('Agregar fila'),
            ),
            TextButton.icon(
              onPressed: _addDate,
              style: TextButton.styleFrom(foregroundColor: c.accent),
              icon: const Icon(Icons.event_rounded),
              label: const Text('Agregar fecha'),
            ),
          ],
        ),
      ],
    );

    return Padding(
      padding:
          EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: ConstrainedBox(
        constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * 0.85),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 8, 8),
              child: Row(
                children: [
                  Expanded(
                    child: Text('Tabla',
                        style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: c.text)),
                  ),
                  TextButton.icon(
                    onPressed: () => Navigator.of(context).pop(true),
                    style: TextButton.styleFrom(foregroundColor: scheme.error),
                    icon: const Icon(Icons.delete_outline_rounded),
                    label: const Text('Eliminar tabla'),
                  ),
                ],
              ),
            ),
            Flexible(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: fields,
              ),
            ),
            Divider(height: 1, color: c.divider),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 12),
              child: Row(
                children: [
                  Text('Total',
                      style: text.copyWith(fontWeight: FontWeight.w700)),
                  const Spacer(),
                  Text(_formatCents(_draft.totalCents),
                      style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          color: c.accent)),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
              child: FilledButton(
                onPressed: () => Navigator.of(context).pop(false),
                style: FilledButton.styleFrom(
                  backgroundColor: c.accent,
                  foregroundColor: scheme.onPrimary,
                  minimumSize: const Size.fromHeight(48),
                ),
                child: const Text('Listo'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
