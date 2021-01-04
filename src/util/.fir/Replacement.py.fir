circuit Test :
  module Test :
    input clock : Clock
    input reset : UInt<1>
    output io : {a : UInt<4>}
  
    wire _T : UInt<15>
    reg _T_1 : UInt<15>, clock with : 
      reset => (reset, UInt<15>("h0"))
    _T <= _T_1
    node _T_2 = bits(_T_1, 14, 14)
    node _T_4 = bits(_T_1, 13, 7)
    node _T_5 = bits(_T_4, 6, 6)
    node _T_7 = bits(_T_4, 5, 3)
    node _T_8 = bits(_T_7, 2, 2)
    node _T_10 = bits(_T_7, 1, 1)
    node _T_11 = bits(_T_10, 0, 0)
    node _T_12 = bits(_T_7, 0, 0)
    node _T_13 = bits(_T_12, 0, 0)
    node _T_9 = mux(_T_8, _T_11, _T_13)
    node _T_14 = cat(_T_8, _T_9)
    node _T_15 = bits(_T_4, 2, 0)
    node _T_16 = bits(_T_15, 2, 2)
    node _T_18 = bits(_T_15, 1, 1)
    node _T_19 = bits(_T_18, 0, 0)
    node _T_20 = bits(_T_15, 0, 0)
    node _T_21 = bits(_T_20, 0, 0)
    node _T_17 = mux(_T_16, _T_19, _T_21)
    node _T_22 = cat(_T_16, _T_17)
    node _T_6 = mux(_T_5, _T_14, _T_22)
    node _T_23 = cat(_T_5, _T_6)
    node _T_24 = bits(_T_1, 6, 0)
    node _T_25 = bits(_T_24, 6, 6)
    node _T_27 = bits(_T_24, 5, 3)
    node _T_28 = bits(_T_27, 2, 2)
    node _T_30 = bits(_T_27, 1, 1)
    node _T_31 = bits(_T_30, 0, 0)
    node _T_32 = bits(_T_27, 0, 0)
    node _T_33 = bits(_T_32, 0, 0)
    node _T_29 = mux(_T_28, _T_31, _T_33)
    node _T_34 = cat(_T_28, _T_29)
    node _T_35 = bits(_T_24, 2, 0)
    node _T_36 = bits(_T_35, 2, 2)
    node _T_38 = bits(_T_35, 1, 1)
    node _T_39 = bits(_T_38, 0, 0)
    node _T_40 = bits(_T_35, 0, 0)
    node _T_41 = bits(_T_40, 0, 0)
    node _T_37 = mux(_T_36, _T_39, _T_41)
    node _T_42 = cat(_T_36, _T_37)
    node _T_26 = mux(_T_25, _T_34, _T_42)
    node _T_43 = cat(_T_25, _T_26)
    node _T_3 = mux(_T_2, _T_23, _T_43)
    node _T_44 = cat(_T_2, _T_3)
    io.a <= _T_44
