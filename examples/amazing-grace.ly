\version "2.24.0"
\header {
  title = "Amazing Grace (Excerpt)"
  composer = "John Newton (1779, public domain)"
  arranger = "Traditional arr."
}
\score {
  <<
    \new Staff \with { instrumentName = "Right Hand" } {
      \clef treble
      \key g \major
      \time 3/4
      \tempo 4 = 72
      r4 r4 d'4 |
      g'2 g'4 |
      b'2 g'4 |
      b'2 a'4 |
      g'2. |
      r4 r4 d'4 |
      g'2 a'4 |
      b'2 d''4 |
      b'2. |
    }
    \new Staff \with { instrumentName = "Left Hand" } {
      \clef bass
      \key g \major
      \time 3/4
      \tempo 4 = 72
      r4 r4 r4 |
      g,4 <b d'>2 |
      c4 <e g>2 |
      d4 <fis a>2 |
      g,4 <b d'>2 |
      r4 r4 r4 |
      g,4 <b d'>2 |
      d4 <fis a>2 |
      g,4 <b d'>2 |
    }
  >>
  \layout { }
  \midi { }
}