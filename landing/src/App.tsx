import { MotionConfig } from 'motion/react'
import { Detection } from './components/Detection'
import { Footer } from './components/Footer'
import { Hero } from './components/Hero'
import { HowItWorks } from './components/HowItWorks'
import { Install } from './components/Install'
import { Nav } from './components/Nav'
import { Security } from './components/Security'

export default function App() {
  return (
    // reducedMotion="user" drops transform animations for visitors who ask for less motion.
    <MotionConfig reducedMotion="user">
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <Detection />
        <Security />
        <Install />
      </main>
      <Footer />
    </MotionConfig>
  )
}
