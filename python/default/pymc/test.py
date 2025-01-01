import pymcprotocol

pymc3e = pymcprotocol.Type3E(plctype="iQ-R")

pymc3e.setaccessopt(commtype="ascii")
pymc3e.connect("192.168.0.201", 20010)

# read from D100 to D110
wordunits_values = pymc3e.batchread_wordunits(headdevice="D100", readsize=10)

# read from X10 to X20
bitunits_values = pymc3e.batchread_bitunits(headdevice="X10", readsize=10)

print(f"word units value : {wordunits_values}")
print(f"bit units value : {bitunits_values}")

#write from Y10 to Y15
#pymc3e.batchwrite_bitunits(headdevice="Y10", values=[0,1,0,1,0])

