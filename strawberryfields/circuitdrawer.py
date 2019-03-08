# Copyright 2019 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""
Circuit drawer
==============

A Strawberry Fields module that provides an object-oriented interface for building
quantum circuit representations of continuous-variable circuits using the
:math:`\LaTeX` `Qcircuit package <https://ctan.org/pkg/qcircuit>`_.

The following features of Qcircuit are currently used:

* Loading Q-circuit: ``\input{Qcircuit}``
* Making Circuits: ``\Qcircuit``
* Spacing: ``@C=#1`` and ``@R=#1``
* Wires: ``\qw[#1]``
* Gates: ``\gate {#1}``, ``\targ``, and ``\qswap``
* Control: ``\ctrl{#1}``

The drawing of the following Xanadu supported operations are currently supported:

.. rst-class:: docstable

+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|     Gate type     |                                                                            Supported gates                                                                             |
+===================+========================================================================================================================================================================+
| Single mode gates | :class:`~.Dgate`, :class:`~.Xgate`, :class:`~.Zgate`, :class:`~.Sgate`, :class:`~.Rgate`, :class:`~.Pgate`, :class:`~.Vgate`, :class:`~.Kgate`, :class:`~.Fouriergate` |
+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Two mode gates    | :class:`~.BSgate`, :class:`~.S2gate`, :class:`~.CXgate`, :class:`~.CZgate`, :class:`~.CKgate`                                                                          |
+-------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

.. note:: Measurement operations :class:`~.MeasureHomodyne`, :class:`~.MeasureHeterodyne`, and :class:`~.MeasureFock` are not currently supported.


Example
-------




Circuit drawer methods
----------------------

.. currentmodule:: strawberryfields.circuitdrawer.Circuit

.. autosummary::
   _gate_from_operator
   parse_op
   _single_mode_gate
   _multi_mode_gate
   _controlled_mode_gate
   _on_empty_column
   _add_column
   _is_empty
   _set_column_spacing
   _set_row_spacing
   _pad_with_spaces
   dump_to_document
   compile_document
   _init_document
   _end_document
   _begin_circuit
   _end_circuit
   _end_wire
   _apply_spacing
    _write_operation_to_document

.. currentmodule:: strawberryfields.circuitdrawer


Code details
^^^^^^^^^^^^
"""
import datetime
import os
from .qcircuit_strings import QUANTUM_WIRE, PAULI_X_COMP, PAULI_Z_COMP, CONTROL, \
    TARGET, COLUMN_SPACING, ROW_SPACING, DOCUMENT_END, WIRE_OPERATION, WIRE_TERMINATOR, CIRCUIT_BODY_TERMINATOR, \
    CIRCUIT_BODY_START, INIT_DOCUMENT, PIPE, D_COMP, R_COMP, P_COMP, V_COMP, FOURIER_COMP, BS_COMP, S_COMP, \
    K_COMP


class ModeMismatchException(Exception):
    """Exception raised when parsing a Gate object

    This class corresponds to the exception raised by :meth:`~.parse_op`
    when an operator is interpreted as an n-mode gate but is applied to a number of modes != n.
    """
    pass


class UnsupportedGateException(Exception):
    """Exception raised when attempting to add an unsupported operator.

    This class corresponds to the exception raised by :meth:`~.parse_op` when it is attempted to add an
    unsupported operator to the circuit.
    """
    pass


class Circuit:
    """Represents a quantum circuit that can be compiled to tex format.

    Args:
        wires (int): the number of quantum wires or subsystems to use in the
            circuit diagram.
    """
    _circuit_matrix = []

    def __init__(self, wires):
        self._document = ''
        self._circuit_matrix = [[QUANTUM_WIRE.format(1)] for wire in range(wires)]
        self._column_spacing = None
        self._row_spacing = None

        self.single_mode_gates = {
            'Xgate': self._x,
            'Zgate': self._z,
            'Dgate': self._d,
            'Sgate': self._s,
            'Rgate': self._r,
            'Pgate': self._p,
            'Vgate': self._v,
            'Kgate': self._k,
            'FourierGate': self._fourier
        }

        self.two_mode_gates = {
            'CXgate': self._cx,
            'CZgate': self._cz,
            'CKgate': self._ck,
            'BSgate': self._bs,
            'S2gate': self._s2
        }

    def _gate_from_operator(self, op):
        """Infers the number of modes and callable Circuit class method that correspond with a Strawberry Fields operator object.

        Args:
            op (strawberryfields.ops.Gate): the Strawberry Fields operator object.

        Returns:
            method (function): callable method that adds the given operator to the latex circuit.
            mode (int): the number of modes affected by the operator gate.
        """
        operator = str(op).split(PIPE)[0]
        method = None
        mode = None

        for two_mode_gate in self.two_mode_gates:
            if two_mode_gate in operator:
                method = self.two_mode_gates[two_mode_gate]
                mode = 2

        if method is None:
            for single_mode_gate in self.single_mode_gates:
                if single_mode_gate in operator:
                    method = self.single_mode_gates[single_mode_gate]
                    mode = 1

        return method, mode

    def parse_op(self, op):
        """Transforms a Strawberry Fields operator object to a latex qcircuit gate.

        Args:
            op (strawberryfields.ops.Gate): the Strawberry Fields operator object.

        Raises:
            UnsupportedGateException: if the operator is not supported by the circuit drawer module.
            ModeMismatchException: if the operator is interpreted as an n-mode gate but is applied to a number of modes != n.

        """
        method, mode = self._gate_from_operator(op)
        wires = list(map(lambda register: register.ind, op.reg))

        if method is None:
            raise UnsupportedGateException('Unsupported operation {0} not printable by circuit builder!'.format(str(op)))
        elif mode == len(wires):
            method(*wires)
        elif mode != len(wires):
            raise ModeMismatchException('{0} mode gate applied to {1} wires!'.format(mode, len(wires)))

    def _x(self, wire):
        """Adds a position displacement operator to the circuit.

        Args:
            wire (int): the subsystem wire to apply the operator to.
        """
        self._single_mode_gate(wire, PAULI_X_COMP)

    def _z(self, wire):
        """Adds a momentum displacement operator to the circuit.

        Args:
            wire (int): the subsystem wire to apply the operator to.
        """
        self._single_mode_gate(wire, PAULI_Z_COMP)

    def _s(self, wire):
        """Adds a squeezing operator to the circuit.

        Args:
            wire (int): the subsystem wire to apply the operator to.
        """
        self._single_mode_gate(wire, S_COMP)

    def _d(self, wire):
        """Adds a displacement operator to the circuit.

        Args:
            wire (int): the subsystem wire to apply the operator to.
        """
        self._single_mode_gate(wire, D_COMP)

    def _r(self, wire):
        """Adds a rotation operator to the circuit.

        Args:
            wire (int): the subsystem wire to apply the operator to.
        """
        self._single_mode_gate(wire, R_COMP)

    def _p(self, wire):
        """Adds a quadratic phase shift operator to the circuit.

        Args:
            wire (int): the subsystem wire to apply the operator to.
        """
        self._single_mode_gate(wire, P_COMP)

    def _v(self, wire):
        """Adds a cubic phase shift operator to the circuit.

        Args:
            wire (int): the subsystem wire to apply the operator to.
        """
        self._single_mode_gate(wire, V_COMP)

    def _k(self, wire):
        """Adds a Kerr operator to the circuit.

        Args:
            wire (int): the subsystem wire to apply the operator to.
        """
        self._single_mode_gate(wire, K_COMP)

    def _fourier(self, wire):
        """Adds a Fourier transform operator to the circuit.

        Args:
            wire (int): the subsystem wire to apply the operator to.
        """
        self._single_mode_gate(wire, FOURIER_COMP)

    def _cx(self, source_wire, target_wire):
        """Adds a controlled position displacement operator to the circuit.

        Args:
            source_wire (int): the controlling subsystem wire.
            target_wire (int): the controlled subsystem wire.
        """
        self._controlled_mode_gate(source_wire, target_wire, TARGET)

    def _cz(self, source_wire, target_wire):
        """Adds a controlled phase operator to the circuit.

        Args:
            source_wire (int): the controlling subsystem wire.
            target_wire (int): the controlled subsystem wire.
        """
        self._controlled_mode_gate(source_wire, target_wire, PAULI_Z_COMP)

    def _ck(self, source_wire, target_wire):
        """Adds a controlled Kerr operator to the circuit.

        Args:
            source_wire (int): the controlling subsystem wire.
            target_wire (int): the controlled subsystem wire.
        """
        self._controlled_mode_gate(source_wire, target_wire, K_COMP)

    def _bs(self, first_wire, second_wire):
        """Adds a beams plitter operator to the circuit.

        Args:
            first_wire (int): the first subsystem wire to apply the operator to.
            second_wire (int): the second subsystem wire to apply the operator to.
        """
        self._multi_mode_gate(BS_COMP, [first_wire, second_wire])

    def _s2(self, first_wire, second_wire):
        """Adds an two mode squeezing operator to the circuit.

        Args:
            first_wire (int): the first subsystem wire to apply the operator to.
            second_wire (int): the second subsystem wire to apply the operator to.
        """
        self._multi_mode_gate(S_COMP, [first_wire, second_wire])

    # operation types

    def _single_mode_gate(self, wire, circuit_op):
        """Adds a single-mode operator gate to the circuit.

        Args:
            circuit_op (str): the latex code for the operator.
            wires (list[int]): a list of the indeces of subsystem wires to apply the multi-mode gate to.
        """
        matrix = self._circuit_matrix
        wire_ops = matrix[wire]

        if Circuit._is_empty(wire_ops[-1]):
            wire_ops[-1] = circuit_op
        else:
            wire_ops.append(circuit_op)
            for prev_wire in matrix[:wire]:
                prev_wire.append(QUANTUM_WIRE.format(1))
            for post_wire in matrix[wire + 1:]:
                post_wire.append(QUANTUM_WIRE.format(1))

    def _multi_mode_gate(self, circuit_op, wires):
        """Adds multiple of the same single-mode operator to the circuit.

        Args:
            circuit_op (str): the latex code for the operator.
            wires (list[int]): a list of the indeces of subsystem wires to apply the gate to.
        """
        matrix = self._circuit_matrix

        if not self._on_empty_column():
            self._add_column()

        for wire in wires:
            wire_ops = matrix[wire]
            wire_ops[-1] = circuit_op
            matrix[wire] = wire_ops

        self._circuit_matrix = matrix

    def _controlled_mode_gate(self, source_wire, target_wire, circuit_op):
        """Adds a controlled operator gate to the circuit.

        Args:
            source wire (int): the index of the controlling subsystem.
            target_wire (int): the index of the controlled subsystem.
            circuit_op (str): the latex code for the operator.
        """
        matrix = self._circuit_matrix
        source_ops = matrix[source_wire]
        target_ops = matrix[target_wire]
        distance = target_wire - source_wire

        if Circuit._is_empty(source_ops[-1]) and Circuit._is_empty(target_ops[-1]):
            source_ops[-1] = CONTROL.format(distance)
            target_ops[-1] = circuit_op
        else:
            for index, wire_ops in enumerate(matrix):
                if index == source_wire:
                    wire_ops.append(CONTROL.format(distance))
                elif index == target_wire:
                    wire_ops.append(circuit_op)
                else:
                    wire_ops.append(QUANTUM_WIRE.format(1))

    # helpers

    def _on_empty_column(self):
        """Checks if the right-most wires for each subsystem in the circuit are all empty

        Returns:
            bool: whether the right-most wires for each subsystem in the circuit are all empty
        """
        matrix = self._circuit_matrix

        empty_column = True
        for wire in enumerate(matrix):
            wire_ops = wire[1]
            if not Circuit._is_empty(wire_ops[-1]):
                empty_column = False
                break

        return empty_column

    def _add_column(self):
        """Adds a unit of quantum wire to each subsystem in the circuit."""
        for wire in self._circuit_matrix:
            wire.append(QUANTUM_WIRE.format(1))

    @staticmethod
    def _is_empty(op):
        """Checks for a NOP, a quantum wire location without an operator.

        Args:
            op (str): latex code for either an operator, or empty quantum wire.

        Returns:
            bool: whether the argument is an empty quantum wire.
        """
        return op == QUANTUM_WIRE.format(1)

    # cosmetic

    def _set_column_spacing(self, spacing):
        """Sets visual spacing between operators in quantum circuit.

        Args:
            spacing (int): spacing between operators.
        """
        self._column_spacing = spacing

    def _set_row_spacing(self, spacing):
        """Sets visual spacing of wires in quantum circuit.

        Args:
            spacing (int): spacing between wires.
        """
        self._row_spacing = spacing

    @staticmethod
    def _pad_with_spaces(string):
        """Pads string with spaces.

        Args:
            string (str): string to pad.

        Returns:
            str: string with space added to either side.
        """
        return ' ' + string + ' '

    # latex translation

    def dump_to_document(self):
        """Writes current circuit to document.

        Returns:
            str: latex document string.
        """
        self._init_document()
        self._apply_spacing()
        self._begin_circuit()

        for wire_ops in enumerate(self._circuit_matrix):
            for wire_op in wire_ops[1]:
                self._write_operation_to_document(wire_op)
            self._end_wire()

        self._end_circuit()
        self._end_document()

        return self._document

    def compile_document(self, tex_dir='./circuit_tex'):
        """Compiles latex documents.

        Args:
            tex_dir (Str): relative directory for latex document output.
        """
        tex_dir = os.path.abspath(tex_dir)
        if not os.path.isdir(tex_dir):
            os.mkdir(tex_dir)
        file_name = "output_{0}".format(datetime.datetime.now().strftime("%Y_%B_%d_%I:%M%p"))
        file_path = '{0}/{1}.tex'.format(tex_dir, file_name)
        output_file = open(file_path, "w+")
        output_file.write(self._document)

        return file_path

    def _init_document(self):
        """Adds the required latex headers to the document."""
        self._document = INIT_DOCUMENT

    def _end_document(self):
        """Appends latex EOD code to the document."""
        self._document += DOCUMENT_END

    def _begin_circuit(self):
        """Prepares document for latex circuit content."""
        self._document += CIRCUIT_BODY_START

    def _end_circuit(self):
        """Ends the latex circuit content."""
        self._document += CIRCUIT_BODY_TERMINATOR

    def _end_wire(self):
        """Ends a wire within the latex circuit."""
        self._document += WIRE_TERMINATOR

    def _apply_spacing(self):
        """Applies wire and operator visual spacing."""
        if self._column_spacing is not None:
            self._document += Circuit._pad_with_spaces(COLUMN_SPACING.format(self._column_spacing))
        if self._row_spacing is not None:
            self._document += Circuit._pad_with_spaces(ROW_SPACING.format(self._row_spacing))

    def _write_operation_to_document(self, operation):
        """Appends operation latex code to circuit in latex document.

        Args:
            operation (str): the latex code for the quantum operation to be applied.
        """
        self._document += Circuit._pad_with_spaces(WIRE_OPERATION.format(operation))

    def __str__(self):
        """String representation of the Circuit class."""
        return self._document
