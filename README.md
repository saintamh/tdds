[![Build Status](https://travis-ci.org/saintamh/tdds.svg?branch=master)](https://travis-ci.org/saintamh/tdds)
[![PyPI version](https://badge.fury.io/py/tdds.svg)](https://pypi.org/project/tdds/)

This package provides immutable data classes for Python2.7 and Python 3.5+

Synopsis
========

You declare a class by listing its fields, and the type of each field

```python
>>> from tdds import Field, Record, seq_of

>>> class Track(Record):
...     title = str
...     total_seconds = int
...
...     @property
...     def duration_str(self):
...         return '%d:%02d' % (self.total_seconds / 60, self.total_seconds % 60)

>>> class Album(Record):
...     artist = str
...     title = str
...     year = Field(int, check=lambda value: 1900 < value < 2050)
...     tracks = seq_of(Track)
```

You instantiate it and access its fields normally

```python
>>> album = Album(
...     artist='Wah-wah',
...     title='Gyroscope',
...     year=2000,
...     tracks=[
...         Track(title="Elevon", total_seconds=209),
...         Track(title="Gear", total_seconds=514),
...         Track(title="Stringer", total_seconds=413),
...         ],
...     )

>>> album.title
'Gyroscope'

>>> album.tracks[0].duration_str
'3:29'
```

Record objects are immutable, hashable and comparable.

```python
>>> album.artist = 'Schwah-schwah'
Traceback (most recent call last):
  ...
tdds.basics.RecordsAreImmutable: Album objects are immutable

>>> Track(title='Hull', total_seconds=7) == Track(title='Hull', total_seconds=7)
True

>>> Track(title='Hull', total_seconds=7) == Track(title='Hold', total_seconds=8)
False
```

The constructor checks the type of each of the given values, and refuses to proceed if the types aren't as declared

```python
>>> Track(title='Fireworks', total_seconds='9')
Traceback (most recent call last):
  ...
tdds.basics.FieldTypeError: Track.total_seconds should be of type int, not str ('9')
```

There are functions to convert to and from Plain Old Data Structures, i.e. just lists and dicts. This is useful e.g. for JSON serialisation.

```python
>>> pods = album.record_pods()

>>> print(json.dumps(pods, indent=4, sort_keys=True))
{
    "artist": "Wah-wah",
    "title": "Gyroscope",
    "tracks": [
        {
            "title": "Elevon",
            "total_seconds": 209
        },
        {
            "title": "Gear",
            "total_seconds": 514
        },
        {
            "title": "Stringer",
            "total_seconds": 413
        }
    ],
    "year": 2000
}

>>> Album.from_pods(album.record_pods()) == album
True
```

Records are also picklable

```python
>>> pickle.loads(pickle.dumps(album)) == album
True
```

The library offers many more features such as automatic type coercion, custom validation functions, enum fields, typed collections,
and more. See the [tests](tests) directory for a specification of sorts.


See also
========

This project is similar in spirit to these other fine libraries:

* [attrs](https://www.attrs.org/)
* [kim](https://kim.readthedocs.io/)
* [cluegen](https://github.com/dabeaz/cluegen)
* [typing.NamedTuple](https://docs.python.org/3.8/library/typing.html#typing.NamedTuple)
* [Scala's case classes](https://docs.scala-lang.org/tour/case-classes.html)

but this one is mine.
