import pytest
from io import StringIO
from metagenomescope.assembly_graph_parser import (
    attempt_to_validate_lastgraph_file,
    sniff_filetype,
    parse_lastgraph,
)


def get_validate_error(glines):
    # What this is doing: create a string consisting of all the lines in
    # glines, separated by newlines, then shove that into a StringIO.
    bad_lg = StringIO("\n".join(glines))
    # Assume that the LastGraph file represented by bad_lg will fail
    # validation, and return the accompanying error message.
    # (If a ValueError *isn't* raised, this'll throw an error saying DID NOT
    # RAISE or something.)
    with pytest.raises(ValueError) as ei:
        attempt_to_validate_lastgraph_file(bad_lg)
    return str(ei.value)


def reset_glines():
    return [
        "2\t10\t1\t1",
        "NODE\t1\t1\t5\t5\t0\t0",
        "G",
        "C",
        "NODE\t2\t6\t20\t5\t0\t0",
        "GGAAGG",
        "TTTTAC",
        "ARC\t1\t2\t5",
        "ARC\t2\t1\t9",
    ]


def test_validate_lastgraph():
    # Try out some known-to-be-correct examples
    with open("metagenomescope/tests/input/cycletest_LastGraph", "r") as ctlg:
        attempt_to_validate_lastgraph_file(ctlg)
    with open("metagenomescope/tests/input/longtest_LastGraph", "r") as ltlg:
        attempt_to_validate_lastgraph_file(ltlg)

    # Okay, now let's try to break things. We'll use glines as a base for
    # the forthcoming cases.
    glines = reset_glines()

    # Here, we test the error where a NODE block is interrupted by the
    # declaration of another NODE.
    # Remove the fourth line of the file (it's 0-indexed, hence 3).
    glines.pop(3)
    assert "Line 4: Node block ends too early." in get_validate_error(glines)

    # Now, test the same thing but with an ARC line being the "interruptor."
    # We'll also do this one line earlier, to switch things up.
    glines = reset_glines()
    glines[2] = "ARC\t1\t1\t5"
    assert "Line 3: Node block ends too early." in get_validate_error(glines)

    # Test cases where the specified number of nodes isn't an int value
    glines = reset_glines()
    glines[0] = "3.5\t10\t1\t1"
    assert "Line 1: $NUMBER_OF_NODES must be an integer" in get_validate_error(
        glines
    )
    glines[0] = "ABC\t10\t1\t1"
    assert "Line 1: $NUMBER_OF_NODES must be an integer" in get_validate_error(
        glines
    )
    glines[0] = "0x123\t10\t1\t1"
    assert "Line 1: $NUMBER_OF_NODES must be an integer" in get_validate_error(
        glines
    )

    # Test insufficient node declarations
    glines = reset_glines()
    glines[4] = "NODE\t2"
    assert (
        "Line 5: Node declaration doesn't include enough fields"
        in get_validate_error(glines)
    )
    glines[4] = "NODE\t2\t6"
    assert (
        "Line 5: Node declaration doesn't include enough fields"
        in get_validate_error(glines)
    )


def test_parse_lastgraph():
    digraph = parse_lastgraph(
        "metagenomescope/tests/input/cycletest_LastGraph"
    )
    # Verify that a NetworkX DiGraph was computed based on this file accurately
    # We expect 4 nodes and 4 edges due to the graph being interpreted as
    # unoriented (i.e. each node's forward or reverse orientation can be used)
    assert len(digraph.nodes) == 4
    assert len(digraph.edges) == 4

    # Check various node attributes individually
    # NOTE that a part of why we check these individually is because, in
    # LastGraph files, the forward and reverse sequences are not perfect
    # reverse complements of each other (they differ by an offset; see
    # https://github.com/rrwick/Bandage/wiki/Assembler-differences for a great
    # explanation of this). So it's acceptable for the GC content of node "ABC"
    # and node "-ABC" to be different.
    assert "1" in digraph.nodes
    assert digraph.nodes["1"]["length"] == 1
    assert digraph.nodes["1"]["depth"] == 5
    assert digraph.nodes["1"]["gc_content"] == 1

    assert "-1" in digraph.nodes
    assert digraph.nodes["-1"]["length"] == 1
    assert digraph.nodes["-1"]["depth"] == 5
    assert digraph.nodes["-1"]["gc_content"] == 0

    assert "2" in digraph.nodes
    assert digraph.nodes["2"]["length"] == 6
    assert digraph.nodes["2"]["depth"] == (20 / 6)
    assert digraph.nodes["2"]["gc_content"] == (2 / 3)

    assert "-2" in digraph.nodes
    assert digraph.nodes["-2"]["length"] == 6
    assert digraph.nodes["-2"]["depth"] == (20 / 6)
    assert digraph.nodes["-2"]["gc_content"] == (1 / 6)


def test_sniff_filetype():
    assert sniff_filetype("asdf.lastgraph") == "lastgraph"
    assert sniff_filetype("asdf.LASTGRAPH") == "lastgraph"
    assert sniff_filetype("asdf_LastGraph") == "lastgraph"
    assert sniff_filetype("asdf.LastGraph") == "lastgraph"
    assert sniff_filetype("gml_LastGraph") == "lastgraph"

    assert sniff_filetype("asdf.gml") == "gml"
    assert sniff_filetype("asdf.GML") == "gml"
    assert sniff_filetype("asdf_gml") == "gml"
    assert sniff_filetype("asdf.gmL") == "gml"
    assert sniff_filetype("gfa_gmL") == "gml"

    assert sniff_filetype("asdf.gfa") == "gfa"
    assert sniff_filetype("asdf.GFA") == "gfa"
    assert sniff_filetype("asdf_gfa") == "gfa"
    assert sniff_filetype("asdf.GfA") == "gfa"
    assert sniff_filetype("fastg_gFa") == "gfa"

    assert sniff_filetype("asdf.fastg") == "fastg"
    assert sniff_filetype("asdf.FASTG") == "fastg"
    assert sniff_filetype("asdf_fastg") == "fastg"
    assert sniff_filetype("aSdF.FaStG") == "fastg"
    assert sniff_filetype("LastGraphfastg") == "fastg"

    with pytest.raises(NotImplementedError):
        sniff_filetype("asdf.asdf")
    with pytest.raises(NotImplementedError):
        sniff_filetype("asdf")


# def test_assemblygraph_constructor_and_sniff_filetype():
#     velvet_g = AssemblyGraph("metagenomescope/tests/input/cycletest_LastGraph")
#
#     gml_g = AssemblyGraph("metagenomescope/tests/input/marygold_fig2a.gml")
#
#     gfa_g = AssemblyGraph("metagenomescope/tests/input/loop.gfa")
#
#     with pytest.raises(NotImplementedError):
#         AssemblyGraph("metagenomescope/tests/input/garbage.thing")