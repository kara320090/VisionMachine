package org.visionmachine.agriclinic

import org.junit.Assert.*
import org.junit.Test

class ReferenceIndexTest {
    @Test fun intervalBoundariesAndTolerancePreserveUnits() {
        val band=ReferenceBand(20.0,30.0,0.5)
        assertEquals(0.0,band.score(20.0),0.0)
        assertEquals(0.0,band.score(30.5),0.0)
        assertEquals(5.0,band.score(31.0),1e-9)
        assertEquals(5.0,band.score(19.0),1e-9)
        assertEquals(100.0,band.score(1000.0),0.0)
    }
    @Test fun weightedIndexIsTransparentAndBounded() {
        assertEquals(60.0,CompositeIndex.weighted(.8,40.0,.5),1e-9)
        assertEquals(80.0,CompositeIndex.weighted(.8,40.0,0.0),1e-9)
        assertEquals(40.0,CompositeIndex.weighted(.8,40.0,1.0),1e-9)
    }
    @Test fun invalidReferencesAndNonFiniteInputsAreRejected() {
        val bad=listOf<()->Unit>({ReferenceBand(20.0,20.0)},{ReferenceBand(30.0,20.0)},{ReferenceBand(20.0,30.0,-1.0)},
            {ReferenceBand(20.0,30.0).score(Double.NaN)},{CompositeIndex.weighted(.8,40.0,Double.NaN)})
        bad.forEach { operation -> try {operation();fail("Invalid reference was accepted")} catch(_:IllegalArgumentException) {} }
    }
}
