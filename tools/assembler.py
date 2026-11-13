# SPDX-License-Identifier: Apache-2.0
"""Versioned assembler for the qualified 0x22 engine; standard library only."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

TARGET = 'od128-sram-v1'
SCHEMA = 'protocol-emulator-program-v1'
CAPACITY = 128
NAME = re.compile(r'[A-Za-z_][A-Za-z_0-9]*\Z')
FIELDS = {
    'SET': ({'mask', 'value', 'oe'}, set()),
    'WAIT': ({'cycles'}, set()),
    'HALT': (set(), set()),
    'WAIT_PIN': ({'pin', 'level', 'timeout'}, {'on_timeout'}),
    'LOOP': ({'count', 'end'}, set()),
    'SHIFT_STEP': ({'tx', 'rx', 'order'}, {'drive', 'payload'}),
    'SHIFT_BURST': ({'tx', 'rx', 'order', 'period'}, set()),
    'DRIVE': ({'tx', 'rx', 'order', 'mask', 'value'}, {'drive', 'payload'}),
    'SAMPLE': ({'tx', 'rx', 'order', 'delay'}, set()),
}
RESERVED = set(FIELDS) | {'TX0', 'TX1', 'fault', 'skip', 'lsb', 'msb', 'push_pull', 'open_drain'}


class AssemblyError(ValueError):
    def __init__(self, line, message):
        self.line = line
        super().__init__(message)


def fail(line, message):
    raise AssemblyError(line, message)


def expression(text, symbols, line):
    """Evaluate bounded integer arithmetic, never arbitrary source code."""
    if len(text) > 256:
        fail(line, 'expression exceeds 256 characters')
    try:
        tree = ast.parse(text, mode='eval')
    except (SyntaxError, ValueError):
        fail(line, f'invalid integer expression: {text!r}')
    if sum(1 for _ in ast.walk(tree)) > 64:
        fail(line, 'expression exceeds 64 syntax nodes')

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            value = node.value
        elif isinstance(node, ast.Name):
            if node.id not in symbols:
                fail(line, f'unknown symbol {node.id!r}')
            value = symbols[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub, ast.Invert)):
            operand = visit(node.operand)
            value = operand if isinstance(node.op, ast.UAdd) else -operand if isinstance(node.op, ast.USub) else ~operand
        elif isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, (ast.LShift, ast.RShift)) and not 0 <= right <= 63:
                fail(line, 'shift count must be 0..63')
            if isinstance(node.op, ast.Add):
                value = left + right
            elif isinstance(node.op, ast.Sub):
                value = left - right
            elif isinstance(node.op, ast.Mult):
                value = left * right
            elif isinstance(node.op, ast.FloorDiv):
                if right == 0:
                    fail(line, 'division by zero')
                value = left // right
            elif isinstance(node.op, ast.LShift):
                value = left << right
            elif isinstance(node.op, ast.RShift):
                value = left >> right
            elif isinstance(node.op, ast.BitOr):
                value = left | right
            elif isinstance(node.op, ast.BitAnd):
                value = left & right
            elif isinstance(node.op, ast.BitXor):
                value = left ^ right
            else:
                fail(line, 'unsupported integer operator')
        else:
            fail(line, 'only integer literals, symbols and integer operators are allowed')
        if value.bit_length() > 64:
            fail(line, 'integer expression exceeds 64 bits')
        return value

    return visit(tree.body)


def operands(text, line):
    fields = {}
    pattern = re.compile(r'([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*?)(?=\s+[A-Za-z_][A-Za-z_0-9]*\s*=|$)')
    position = 0
    for match in pattern.finditer(text):
        if text[position:match.start()].strip():
            fail(line, 'operands must use name=expression separated by spaces')
        name, value = match.groups()
        if name in fields:
            fail(line, f'duplicate operand {name!r}')
        if not value.strip():
            fail(line, f'missing value for {name!r}')
        fields[name] = value.strip()
        position = match.end()
    if text[position:].strip():
        fail(line, 'operands must use name=expression separated by spaces')
    return fields


def encode(op, raw, symbols, pc, length, line):
    required, optional = FIELDS[op]
    if set(raw) - required - optional:
        fail(line, 'unknown operand(s): ' + ', '.join(sorted(set(raw) - required - optional)))
    if required - set(raw):
        fail(line, 'missing operand(s): ' + ', '.join(sorted(required - set(raw))))
    args = {}

    def number(key, low, high):
        value = expression(raw[key], symbols, line)
        if not low <= value <= high:
            fail(line, f'{key} must be {low}..{high}, got {value}')
        args[key] = value
        return value

    def choice(key, choices, default=None):
        value = raw.get(key, default)
        if value not in choices:
            fail(line, f'{key} must be ' + '/'.join(choices))
        args[key] = value
        return choices.index(value)

    minimum = maximum = 1
    flow = {'next': pc + 1}
    if op == 'SET':
        word = number('mask', 0, 255) << 16 | number('oe', 0, 255) << 8 | number('value', 0, 255)
    elif op == 'WAIT':
        cycles = number('cycles', 0, 65535)
        word, minimum, maximum = 0x40000000 | cycles, cycles + 1, cycles + 1
    elif op == 'HALT':
        word, flow = 0x80000000, {'terminal': 'HALT'}
    elif op == 'WAIT_PIN':
        word = 0xC0000000 | number('pin', 0, 7) << 27 | number('level', 0, 1) << 26
        word |= number('timeout', 0, 65535)
        maximum = args['timeout'] + 1
        target = raw.get('on_timeout', 'fault')
        if target == 'fault':
            args['on_timeout'] = 'fault'
            flow['failure'] = 'FAULT'
        elif target == 'skip':
            if pc + 2 >= length:
                fail(line, 'timeout skip destination is outside the loaded program')
            word |= 1 << 25
            args['on_timeout'] = 'skip'
            flow['failure'] = pc + 2
        else:
            destination = number('on_timeout', 0, length - 1)
            word |= 1 << 24 | destination << 16
            flow.update(failure=destination, failure_aborts_loop_and_shift=True)
    elif op == 'LOOP':
        count = number('count', 0, 255)
        end = number('end', pc + 2, length - 1)
        body = end - pc - 1
        if body > 31:
            fail(line, f'LOOP body has {body} words; maximum is 31')
        word = 0x60000000 | body << 24 | count
        flow = {'body_start': pc + 1, 'body_end': end, 'repeats': count}
    else:
        tx, rx = number('tx', 0, 7), number('rx', 0, 7)
        if tx == rx:
            fail(line, 'tx and rx must be different pins')
        order = choice('order', ['lsb', 'msb'])
        word = 0xA0000000 | order << 28 | tx << 25 | rx << 22
        if op in ('SHIFT_STEP', 'DRIVE'):
            word |= choice('drive', ['push_pull', 'open_drain'], 'push_pull')
            word |= choice('payload', ['TX0', 'TX1'], 'TX0') << 1
        if op == 'SHIFT_BURST':
            period = number('period', 2, 65535)
            word |= 1 << 21 | period << 5
            minimum = maximum = 8 * period
        elif op == 'DRIVE':
            mask = number('mask', 0, 255)
            if mask & ((1 << tx) | (1 << rx)):
                fail(line, 'DRIVE mask must exclude tx and rx pins')
            word |= 1 << 19 | mask << 11 | number('value', 0, 255) << 3
        elif op == 'SAMPLE':
            delay = number('delay', 0, 65535)
            word |= 2 << 19 | delay << 3
            minimum = maximum = delay + 1
    return {'pc': pc, 'line': line, 'opcode': op, 'operands': args,
            'word': f'{word:08x}', 'spacing_edges': {'min': minimum, 'max': maximum}, 'flow': flow}


def schedule(instructions):
    """Expand deterministic dispatch/loops, stopping at external input choices."""
    pc, edge = 0, 1
    loop = None
    first, last, counts = {}, {}, Counter()
    while pc < len(instructions):
        inst = instructions[pc]
        first.setdefault(pc, edge)
        last[pc] = edge
        counts[pc] += 1
        if inst['opcode'] == 'WAIT_PIN':
            status, halt = 'INPUT_DEPENDENT', None
            break
        if inst['opcode'] == 'HALT':
            status, halt = 'FIXED_DISPATCH', edge
            break
        edge += inst['spacing_edges']['max']
        if inst['opcode'] == 'LOOP':
            flow = inst['flow']
            if flow['repeats'] == 0:
                pc = flow['body_end']
                continue
            loop = dict(flow)
        pc += 1
        if loop is not None and pc == loop['body_end']:
            loop['repeats'] -= 1
            if loop['repeats']:
                pc = loop['body_start']
            else:
                loop = None
    else:
        status, halt = 'FALLTHROUGH_FAULT', None
    return {'status': status, 'halt_edge': halt,
            'scope': 'Dispatch assuming valid runtime shift sequencing, continuous enable and no reset; input choices stop expansion.',
            'positions': {str(pc): {'first_edge': first[pc], 'last_edge': last[pc], 'executions': counts[pc]}
                          for pc in sorted(counts)}}


def assemble(source):
    source = source.replace('\r\n', '\n').replace('\r', '\n')
    symbols, constants, labels, pending = {}, {}, {}, []
    payloads, idle_inputs = {'TX0': 0, 'TX1': 0}, 0
    data_seen, target_seen, idle_seen = set(), False, False

    def define(name, value, line):
        if not NAME.fullmatch(name) or name in RESERVED:
            fail(line, f'invalid or reserved symbol {name!r}')
        if name in symbols:
            fail(line, f'duplicate symbol {name!r}')
        symbols[name] = value

    for line, original in enumerate(source.splitlines(), 1):
        text = original.split(';', 1)[0].strip()
        if not text:
            continue
        if not target_seen:
            if text.split() != ['.target', TARGET]:
                fail(line, f'first statement must be .target {TARGET}')
            target_seen = True
            continue
        if text.startswith('.target'):
            fail(line, 'duplicate or unsupported target declaration')
        if text.startswith('.const '):
            parts = text.split(None, 2)
            if len(parts) != 3:
                fail(line, 'use .const NAME expression')
            value = expression(parts[2], constants, line)
            define(parts[1], value, line)
            constants[parts[1]] = value
            continue
        if text.startswith('.data '):
            parts = text.split(None, 2)
            if len(parts) != 3 or parts[1] not in payloads:
                fail(line, 'use .data TX0/TX1 byte-expression')
            key = parts[1]
            if key in data_seen:
                fail(line, f'duplicate payload initialization {key}')
            value = expression(parts[2], constants, line)
            if not 0 <= value <= 255:
                fail(line, 'payload must be 0..255')
            payloads[key] = value
            data_seen.add(key)
            continue
        if text.startswith('.idle '):
            if idle_seen:
                fail(line, 'duplicate idle-input declaration')
            idle_inputs = expression(text.split(None, 1)[1], constants, line)
            if not 0 <= idle_inputs <= 255:
                fail(line, 'idle inputs must be 0..255')
            idle_seen = True
            continue
        label = re.match(r'^([A-Za-z_][A-Za-z_0-9]*):\s*(.*)$', text)
        if label:
            name, text = label.groups()
            define(name, len(pending), line)
            labels[name] = len(pending)
            if not text:
                continue
        parts = text.split(None, 1)
        op = parts[0]
        if op not in FIELDS:
            fail(line, f'unknown instruction or directive {op!r}')
        pending.append((op, operands(parts[1] if len(parts) == 2 else '', line), line, text))
        if len(pending) > CAPACITY:
            fail(line, f'program exceeds {CAPACITY} words; no truncation is permitted')
    if not pending:
        fail(1, 'program is empty')
    instructions = []
    for pc, (op, fields, line, text) in enumerate(pending):
        inst = encode(op, fields, symbols, pc, len(pending), line)
        inst['source'] = text
        instructions.append(inst)
    warnings = []
    for inst in instructions:
        if inst['opcode'] == 'LOOP' and inst['operands']['count']:
            for child in instructions[inst['pc'] + 1:inst['operands']['end']]:
                if child['opcode'] in ('HALT', 'LOOP') or child['operands'].get('on_timeout') == 'skip':
                    fail(child['line'], 'HALT, nested LOOP or legacy timeout skip in a nonzero LOOP body')
        if inst['opcode'] == 'WAIT_PIN':
            destination = inst['flow']['failure']
            if type(destination) is int and destination <= inst['pc']:
                warnings.append(f"line {inst['line']}: backward timeout branch; finite total runtime is not established")
    timing = schedule(instructions)
    if timing['status'] == 'FALLTHROUGH_FAULT':
        warnings.append('execution falls beyond the loaded program and faults; add an explicit HALT if unintended')
    words = [inst['word'] for inst in instructions]
    binary = b''.join(int(word, 16).to_bytes(4, 'little') for word in words)
    return {'schema': SCHEMA, 'target': TARGET, 'interface_id': 0x22, 'capacity_words': CAPACITY,
            'byte_order': 'little', 'word_bytes': 4, 'source_sha256': hashlib.sha256(source.encode('utf-8')).hexdigest(),
            'binary_sha256': hashlib.sha256(binary).hexdigest(), 'words': words,
            'payloads': payloads, 'idle_inputs': idle_inputs, 'labels': labels,
            'constants': constants, 'instructions': instructions, 'schedule': timing, 'warnings': warnings}


def program_bytes(image):
    if image.get('schema') != SCHEMA or image.get('target') != TARGET or image.get('interface_id') != 0x22:
        raise ValueError('unsupported program format, target or interface')
    words = image['words']
    if not 1 <= len(words) <= CAPACITY or any(not isinstance(w, str) or not re.fullmatch('[0-9a-f]{8}', w) for w in words):
        raise ValueError('invalid program words or capacity')
    binary = b''.join(int(w, 16).to_bytes(4, 'little') for w in words)
    if hashlib.sha256(binary).hexdigest() != image['binary_sha256']:
        raise ValueError('program binary checksum mismatch')
    return binary


def load_plan(image, *, payloads=None, idle_inputs=None):
    binary = program_bytes(image)
    data = dict(image['payloads'])
    if payloads:
        if not set(payloads) <= {'TX0', 'TX1'}:
            raise ValueError('unknown payload register')
        data.update(payloads)
    idle = image['idle_inputs'] if idle_inputs is None else idle_inputs
    if set(data) != {'TX0', 'TX1'} or any(type(v) is not int or not 0 <= v <= 255 for v in [idle, *data.values()]):
        raise ValueError('payloads and idle inputs must be bytes')
    steps = []

    def step(action, ui, data_in=0, *, ena=1, reset=1, drive=True, **expected):
        steps.append({'action': action, 'rst_n': reset, 'ena': ena, 'ui_in': ui,
                      'uio_in': data_in, 'host_drives_uio': drive, 'expected': expected})

    step('reset', 0, ena=0, reset=0, drive=False, uio_oe=0)
    step('identify', 0x67, ena=0, drive=False, uio_oe=0, uo_out=0x22)
    for offset, byte in enumerate(binary):
        if offset % 32 == 0:
            step('write_bank', 0xE5, offset // 32, uio_oe=0)
        step('write_byte', 0xC0 | offset % 32, byte, uio_oe=0)
    for offset, byte in enumerate(binary):
        if offset % 32 == 0:
            step('read_bank', 0xE5, offset // 32, uio_oe=0)
        step('read_byte_after_edge', 0x80 | offset % 32, ena=0, drive=False, uio_oe=255, uio_out=byte)
    step('commit_length', 0xE0, len(image['words']), uio_oe=0)
    step('read_length', 0xA0, ena=0, drive=False, uio_oe=255, uio_out=len(image['words']))
    for name, address in (('TX0', 1), ('TX1', 4)):
        step('write_' + name, 0xE0 | address, data[name], uio_oe=0)
        step('read_' + name, 0xA0 | address, ena=0, drive=False, uio_oe=255, uio_out=data[name])
    for _ in range(2):
        step('flush_idle', 0, idle, ena=0, drive=False, uio_oe=0, uo_out=0x20)
    return {'schema': 'protocol-emulator-load-plan-v1', 'target': TARGET,
            'binary_sha256': image['binary_sha256'], 'steps': steps,
            'sampling': 'Each step holds inputs through one rising edge; check expected outputs after settling. Abort on mismatch.',
            'ownership': 'External devices must release shared pins during loader reads. Flush input levels come from the attached idle environment.',
            'run': {'rst_n': 1, 'ena': 1, 'ui_in': 0, 'first_edge': 'The next rising edge executes program word zero.'}}


def listing(image):
    program_bytes(image)
    lines = [f"Target {TARGET}; interface 0x22; {len(image['words'])}/{CAPACITY} words",
             'Spacing is accepted edges from instruction execution to the next instruction.',
             'Fixed positions assume valid shift sequencing, continuous enable and no reset.',
             'Input waits depend on synchronized inputs; final-edge match wins. Disabled time is excluded.',
             'PC   WORD      SPACING     FIRST..LAST / EXECUTIONS  SOURCE',
             '---- --------  ----------  ------------------------  ------']
    positions = image['schedule']['positions']
    for inst in image['instructions']:
        cost = inst['spacing_edges']
        spacing = str(cost['min']) if cost['min'] == cost['max'] else f"{cost['min']}..{cost['max']}"
        position = positions.get(str(inst['pc']))
        shown = f"{position['first_edge']}..{position['last_edge']} / {position['executions']}" if position else 'conditional or unreachable'
        lines.append(f"{inst['pc']:03d}  {inst['word']}  {spacing:10}  {shown:24}  {inst['source']}")
        if inst['opcode'] in ('WAIT_PIN', 'LOOP'):
            lines.append('     flow: ' + json.dumps(inst['flow'], sort_keys=True))
    lines.extend([f"Schedule: {image['schedule']['status']}; HALT edge: {image['schedule']['halt_edge']}",
                  'Clock target: 50 MHz. This is not an Fmax measurement or analog timing guarantee.'])
    lines.extend('WARNING: ' + warning for warning in image['warnings'])
    return '\n'.join(lines) + '\n'


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def artifacts(image):
    return {'program.bin': program_bytes(image), 'program.json': json_bytes(image),
            'program.lst': listing(image).encode('utf-8'), 'load-plan.json': json_bytes(load_plan(image))}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Assemble readable programs for qualified interface 0x22.')
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', type=Path, required=True, help='new output directory (never overwrites a prior build)')
    args = parser.parse_args(argv)
    try:
        image = assemble(args.source.read_text(encoding='utf-8'))
        files = artifacts(image)
        if args.out.exists():
            raise ValueError('output directory already exists; choose a new --out path')
        args.out.mkdir(parents=True)
        for name, raw in files.items():
            (args.out / name).write_bytes(raw)
    except AssemblyError as error:
        parser.exit(2, f'{args.source}:{error.line}: error: {error}\n')
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(2, f'{args.source}: error: {error}\n')
    print(f"Assembled {len(image['words'])}/{CAPACITY} words for {TARGET}: {args.out}")
    for warning in image['warnings']:
        print('WARNING: ' + warning)
    return 0


if __name__ == '__main__':
    sys.exit(main())
