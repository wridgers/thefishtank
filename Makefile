# Builds The Fish Tank: the parametric FreeCAD models (cad/*.FCStd), the print-ready STLs (stls/), the
# assembly with its interference check, the renders (renders/, with a README showing them), and the BOM
# (BOM.md).
#
#   make                  everything
#   make parts            only the printed parts (no FreeCAD GUI or STEP models needed)
#   make clean            remove everything generated
#
# Needs FreeCAD 1.1. If it isn't on PATH, point at it, e.g.
#   make FREECADCMD=/opt/freecad/usr/bin/freecadcmd FREECAD=/opt/freecad/usr/bin/freecad
# The assembly runs in the FreeCAD GUI, so it needs a display; without one it runs under xvfb-run.

FREECADCMD ?= freecadcmd
FREECAD ?= freecad
XVFB ?= $(if $(DISPLAY),,xvfb-run -a)

# Reference models the assembly imports. The NF-A12x25 model (djos_1475, Printables 273355) stands in
# for the ARCTIC P12 Pro; it is public domain and kept here. The BC-250 model's licence doesn't allow
# redistributing it, so download it yourself (see the rule below). A STEP of the 120x15 slim fan is
# optional (SLIM_FAN_STEP=...).
BC_STEP ?= cad/step/bc250.step
FAN_STEP ?= cad/step/nf-a12x25.step

# every FreeCAD file lives in cad/ (the generated parts, the reference models and the assembly)
SHROUD_FCSTD := $(addprefix cad/,fan_shroud_push.FCStd fan_shroud_pull.FCStd pcb_clamp.FCStd \
                backfan_mount.FCStd fan_hub_frame.FCStd fan_isolation_tpu.FCStd)
FRAME_FCSTD := cad/fish_tank_frame.FCStd
ASSEMBLY := cad/fish_tank.FCStd
RENDERS := $(addprefix renders/,$(addsuffix .png,case_front_left case_back_right case_front case_back \
           case_left case_right lying_front lying_side frame_front_left frame_back_right))

.PHONY: all parts assembly clean relock
.DELETE_ON_ERROR:

all: parts assembly

parts: $(SHROUD_FCSTD) $(FRAME_FCSTD)

assembly: $(ASSEMBLY) $(RENDERS) renders/README.md BOM.md

# $(1): GEN_MAIN value, $(2): script. STL names take an [a]_ prefix for accent parts and _xN for the
# quantity; the scripts remove a part's earlier STLs before writing it. freecadcmd exits 0 even when
# the script fails, so the log is checked for exceptions and failed body checks.
define generate
	@mkdir -p stls logs
	GEN_MAIN=$(1) OUTDIR=. LOCK_UPDATE=$(LOCK_UPDATE) $(FREECADCMD) $(2) > logs/$(1).log 2>&1
	@rm -rf scripts/__pycache__  # FreeCAD's Python caches the imported scripts here
	@if tr '\r' '\n' < logs/$(1).log | grep -a 'Exception while processing\|ok=False\|SKETCH\|state='; then \
	    echo "$(2) failed: see logs/$(1).log"; exit 1; fi
	@grep -ao '[^ ]*: valid=.*\|[^ ]*: print check:.*' logs/$(1).log
endef

# the board module: shrouds, PCB clamps, backplate fan mount, fan hub frame, TPU fan parts
$(SHROUD_FCSTD) &: scripts/gen_shrouds.py
	$(call generate,shrouds,scripts/gen_shrouds.py)

# the enclosure: frame, panels and the other printed parts; gen_frame.py borrows helpers from gen_shrouds.py
$(FRAME_FCSTD) &: scripts/gen_frame.py scripts/gen_shrouds.py
	$(call generate,frame,scripts/gen_frame.py)

# The assembly script also writes the reference models into cad/, re-saves the printed parts with
# their colours, checks every pair of parts for overlaps, and writes the BOM. Then the renders: a
# FreeCAD run per section, from the saved file (see shots_stage). It re-saves the part files, which are
# also its inputs, so its own outputs are touched afterwards to keep make from rerunning it.
$(ASSEMBLY) $(RENDERS) renders/README.md BOM.md &: scripts/build_assembly.py $(SHROUD_FCSTD) $(FRAME_FCSTD) $(BC_STEP) $(FAN_STEP)
	@mkdir -p logs renders
	OUTDIR=$(CURDIR) BC_STEP=$(abspath $(BC_STEP)) FAN_STEP=$(abspath $(FAN_STEP)) \
	    SLIM_FAN_STEP=$(if $(SLIM_FAN_STEP),$(abspath $(SLIM_FAN_STEP))) LOG=$(CURDIR)/logs/assembly.log \
	    $(XVFB) $(FREECAD) scripts/build_assembly.py > /dev/null 2>&1
	@grep -q 'saved' logs/assembly.log || { cat logs/assembly.log; exit 1; }
	@grep 'bad objects\|INTERFERENCE\|checking' logs/assembly.log
	for k in 0 1 2; do \
	    SECTION=$$k STAGE=shots OUTDIR=$(CURDIR) LOG=$(CURDIR)/logs/shots_$$k.log \
	        SHOTS=$(CURDIR)/renders $(XVFB) $(FREECAD) scripts/build_assembly.py > /dev/null 2>&1; \
	    grep -q 'shots done' logs/shots_$$k.log || { cat logs/shots_$$k.log; exit 1; }; \
	done
	@rm -rf scripts/__pycache__
	@touch $(ASSEMBLY) $(RENDERS) renders/README.md BOM.md

$(BC_STEP):
	@echo "Missing $@: download the STEP from \"Accurate 3D model of the AMD BC-250 board\" by torassk"
	@echo "(https://www.printables.com/model/1341336) and save it as $@, or set BC_STEP=<path>."
	@exit 1

clean:
	rm -f $(SHROUD_FCSTD) $(FRAME_FCSTD) $(ASSEMBLY) BOM.md
	rm -f $(addprefix cad/,bc250_board.FCStd fan_120x25.FCStd fan_120x15.FCStd psu_flex_atx.FCStd \
	      usb_hub_anker.FCStd fan_hub.FCStd power_button_16mm.FCStd hardware_m3.FCStd)
	rm -f stls/*.stl  # keeps the READMEs
	rm -rf logs renders

# Printed parts in use are locked (cad/locked.json): a build that changes one fails. To accept the
# change (or lock more parts), regenerate them with their new fingerprints, then rebuild the rest:
#   make relock                       every locked part
#   make relock PARTS=a.stl,b.stl     just these (and lock them if they aren't yet)
relock:
	$(MAKE) -B parts LOCK_UPDATE=$(or $(PARTS),all)
	$(MAKE)
