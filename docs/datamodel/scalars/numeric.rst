.. _ref_datamodel_scalars_numeric:

Number Types
============

.. eql:type:: std::decimal

    :index: numeric float

    Any number of arbitrary precision.

    All of the following types can be cast into numeric:
    :eql:type:`int16`, :eql:type:`int32`, :eql:type:`int64`,
    :eql:type:`float32`, and :eql:type:`float64`.

.. eql:type:: std::int16

    :index: int

    A 16-bit signed integer.

.. eql:type:: std::int32

    :index: int

    A 32-bit signed integer.

.. eql:type:: std::int64

    :index: int

    A 64-bit signed integer.

.. eql:type:: std::float32

    :index: float

    A variable precision, inexact number.

    Minimal guaranteed precision is at least 6 decimal digits.

.. eql:type:: std::float64

    :index: float

    A variable precision, inexact number.

    Minimal guaranteed precision is at least 15 decimal digits.


Abstract Number Types
=====================

.. eql:type:: std::anyint

    :index: anytype int

    Abstract base scalar type for
    :eql:type:`int16`, :eql:type:`int32`, and :eql:type:`int64`.

.. eql:type:: std::anyfloat

    :index: anytype float

    Abstract base scalar type for
    :eql:type:`float32` and :eql:type:`float64`.

.. eql:type:: std::anyreal

    :index: anytype

    Abstract base scalar type for
    :eql:type:`anyint`, :eql:type:`anyfloat`, and :eql:type:`decimal`.
