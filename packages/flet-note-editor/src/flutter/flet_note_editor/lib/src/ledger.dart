part of 'note_editor.dart';

// ── Dated table ────────────────────────────────────────
//
// A block embed of type "ledger": a merged header cell with a date, then
// "Descripción | Valor" rows and the total of the values in the last row.
// The Delta stores it as {"insert": {"ledger": "<json>"}} with
// {"date": "15/11/2026", "rows": [{"description": "...", "value": "..."}]}.
//
// Values keep the typed text. Dots group thousands and a comma starts the
// decimals, like the calculator. The Python side
// (features/notes/domain/note_table.py) parses them with the same rules.

const _ledgerType = 'ledger';

class _LedgerRow {
  _LedgerRow([this.description = '', this.value = '']);

  String description;
  String value;

  bool get isBlank => description.trim().isEmpty && value.trim().isEmpty;
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
          if (row is Map)
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
        'rows': [
          for (final row in rows)
            {'description': row.description, 'value': row.value},
        ],
      });

  _LedgerData copy() => _LedgerData(
        date: date,
        rows: [for (final row in rows) _LedgerRow(row.description, row.value)],
      );

  /// Trimmed, without the rows left completely empty.
  _LedgerData compact() => _LedgerData(
        date: date.trim(),
        rows: [
          for (final row in rows)
            if (!row.isBlank)
              _LedgerRow(row.description.trim(), row.value.trim()),
        ],
      );

  int get totalCents =>
      rows.fold(0, (sum, row) => sum + (_parseCents(row.value) ?? 0));
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
  const _LedgerEmbedBuilder({required this.colors, required this.onOpen});

  final _Palette colors;
  final void Function(Embed node) onOpen;

  @override
  String get key => _ledgerType;

  @override
  Widget build(BuildContext context, EmbedContext embedContext) {
    final node = embedContext.node;
    return _LedgerView(
      data: _LedgerData.decode(node.value.data),
      colors: colors,
      onTap: embedContext.readOnly ? null : () => onOpen(node),
    );
  }
}

/// The table as it sits in the note. Tapping it opens [_LedgerSheet].
class _LedgerView extends StatelessWidget {
  const _LedgerView({required this.data, required this.colors, this.onTap});

  final _LedgerData data;
  final _Palette colors;
  final VoidCallback? onTap;

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

    final date = data.date.trim();
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 8),
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(
          border: Border.fromBorderSide(line),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // The merged cell across both columns.
            Container(
              color: colors.accentContainer,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.event_rounded, size: 18, color: colors.accent),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      date.isEmpty ? 'dd/mm/aaaa' : date,
                      style: date.isEmpty
                          ? base.copyWith(color: colors.muted)
                          : strong,
                    ),
                  ),
                ],
              ),
            ),
            Table(
              columnWidths: const {
                0: FlexColumnWidth(3),
                1: FlexColumnWidth(2),
              },
              border: TableBorder(
                  top: line, horizontalInside: line, verticalInside: line),
              children: [
                TableRow(children: [
                  cell('Descripción', label),
                  cell('Valor', label, end: true),
                ]),
                for (final row in data.rows)
                  TableRow(children: [
                    cell(row.description, base),
                    cell(
                      row.value,
                      row.value.trim().isNotEmpty &&
                              _parseCents(row.value) == null
                          ? base.copyWith(color: error)
                          : base,
                      end: true,
                    ),
                  ]),
                if (data.rows.isEmpty)
                  TableRow(children: [
                    cell(onTap == null ? 'Sin filas' : 'Toca para agregar filas',
                        base.copyWith(color: colors.muted)),
                    cell('', base),
                  ]),
                TableRow(
                  decoration: BoxDecoration(
                      color: colors.accentContainer.withValues(alpha: 0.45)),
                  children: [
                    cell('Total', strong),
                    cell(_formatCents(data.totalCents), strong, end: true),
                  ],
                ),
              ],
            ),
          ],
        ),
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

class _RowFields {
  _RowFields(_LedgerRow row)
      : description = TextEditingController(text: row.description),
        value = TextEditingController(text: row.value);

  final TextEditingController description;
  final TextEditingController value;

  void dispose() {
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
      ..rows = [
        for (final row in _rows)
          _LedgerRow(row.description.text, row.value.text),
      ];
  }

  void _changed() => setState(_sync);

  void _today() {
    final now = DateTime.now();
    _date.text = '${_twoDigits(now.day)}/${_twoDigits(now.month)}/${now.year}';
    _changed();
  }

  void _addRow() {
    final row = _RowFields(_LedgerRow());
    _rows.add(row);
    _added = row;
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

  @override
  Widget build(BuildContext context) {
    final c = widget.colors;
    final scheme = Theme.of(context).colorScheme;
    final text = TextStyle(fontSize: 15, color: c.text);
    final label =
        TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: c.muted);

    final fields = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TextField(
          controller: _date,
          autofocus: widget.isNew,
          keyboardType: TextInputType.number,
          inputFormatters: [_DateFormatter()],
          textAlign: TextAlign.center,
          cursorColor: c.accent,
          style: text.copyWith(fontWeight: FontWeight.w700),
          decoration: _decoration(
            'dd/mm/aaaa',
            suffix: TextButton(
              onPressed: _today,
              style: TextButton.styleFrom(foregroundColor: c.accent),
              child: const Text('Hoy'),
            ),
          ),
          onChanged: (_) => _changed(),
        ),
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
            padding: const EdgeInsets.only(top: 8),
            child: Row(
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
                SizedBox(
                  width: 40,
                  child: IconButton(
                    tooltip: 'Quitar fila',
                    icon: Icon(Icons.close_rounded, size: 20, color: c.muted),
                    onPressed: () => _removeRow(row),
                  ),
                ),
              ],
            ),
          ),
        Align(
          alignment: AlignmentDirectional.centerStart,
          child: TextButton.icon(
            onPressed: _addRow,
            style: TextButton.styleFrom(foregroundColor: c.accent),
            icon: const Icon(Icons.add_rounded),
            label: const Text('Agregar fila'),
          ),
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
