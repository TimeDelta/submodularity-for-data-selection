#!/bin/bash

regex2fst "(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER) (ONE|FIRST|TWO|SECOND|THREE|THIRD|FOUR|FOURTH|FIVE|FIFTH|SIX|SIXTH|SEVEN|SEVENTH|EIGHT|EIGHTH|NINE|NINETH|TEN|TENTH|ELEVEN|ELEVENTH|TWELVE|TWELFTH|THIRTEEN|THIRTEENTH|FOURTEEN|FOURTEENTH|FIFTEEN|FIFTEENTH|SIXTEEN|SIXTEENTH|SEVENTEEN|SEVENTEENTH|EIGHTEEN|EIGHTEENTH|NINETEEN|NINETEENTH|TWENTY|TWENTIETH|(TWENTY (ONE|FIRST|TWO|SECOND|THREE|THIRD|FOUR|FOURTH|FIVE|FIFTH|SIX|SIXTH|SEVEN|SEVENTH|EIGHT|EIGHTH|NINE|NINETH))|(TWENTY FIRST)|(TWENTY TWO)|(TWENTY SECOND)|(TWENTY THREE)|(TWENTY THIRD)|(TWENTY FOUR)|(TWENTY FOURTH)|(TWENTY FIVE)|(TWENTY FIFTH)|(TWENTY SIX)|(TWENTY SIXTH)|(TWENTY SEVEN)|(TWENTY SEVENTH)|(TWENTY EIGHT)|(TWENTY EIGHTH)|(TWENTY NINE)|(TWENTY NINETH)|(THIRTY)|(THIRTIETH)|(THIRTY ONE)|(THIRTY FIRST))? ((NINETEEN( OH)?|(TWO THOUSAND)) (ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|((TWENTY|THIRTY|FORTY|FIFTY|SIXTY|SEVENTY|EIGHTY|NINETY)( (ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE))?)))?" date.fst

fstminimize date.fst date.min.fst

fstcompile --isymbols=mapper.syms --osymbols=mapper.syms --keep_isymbols --keep_osymbols mapper.txt mapper.fst

fstprint date.min.fst > date.min.txt

fstcompile --isymbols=mapper.syms --osymbols=mapper.syms --keep_isymbols --keep_osymbols date.min.txt date.syms.fst

fstcompose mapper.fst date.syms.fst date_mapper.fst

fstclosure date_mapper.fst date_mapper.cl.fst
