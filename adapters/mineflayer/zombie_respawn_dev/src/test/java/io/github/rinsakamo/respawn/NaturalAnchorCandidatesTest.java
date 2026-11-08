package io.github.rinsakamo.respawn;

import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Pure geometry negative controls; does not instantiate or weaken a World. */
public final class NaturalAnchorCandidatesTest {
    public static void main(String[] args) {
        List<int[]> candidates = NaturalAnchorCandidates.offsets();
        assert candidates.size() == 16 * 17 : "bounded candidate count";
        assert candidates.getFirst()[0] == 6;
        assert candidates.getFirst()[1] == 0;
        assert candidates.getFirst()[2] == 0;
        Set<String> seen = new HashSet<>();
        boolean otherHeight = false;
        boolean otherDirection = false;
        for (int[] d : candidates) {
            int squared = d[0] * d[0] + d[2] * d[2];
            assert 16 <= squared && squared <= 81 : "no remote/zero distance sites";
            assert Math.abs(d[1]) <= 8 : "bounded slope search";
            assert seen.add(d[0] + ":" + d[1] + ":" + d[2]) : "unique proposals";
            otherHeight |= d[1] != 0;
            otherDirection |= d[0] != 6 || d[2] != 0;
        }
        assert otherHeight && otherDirection;
        // This check is NOT a safeAnchor acceptance proof: actual Paper
        // passability and supporting block checks are always still required.
        System.out.println("NATURAL_ANCHOR_CANDIDATE_SOURCE_PASS");
    }
}
