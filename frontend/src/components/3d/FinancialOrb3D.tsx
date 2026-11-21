import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

interface FinancialOrb3DProps {
  className?: string;
  size?: number;
}

export const FinancialOrb3D: React.FC<FinancialOrb3DProps> = ({
  className = '',
  size = 320,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const currentMount = mountRef.current;
    if (!currentMount) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    camera.position.z = 5;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(size, size);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    currentMount.appendChild(renderer.domElement);

    // Group to hold all orb elements
    const orbGroup = new THREE.Group();
    scene.add(orbGroup);

    // 1. Central Core Sphere (Glowing Wireframe / Icosahedron)
    const coreGeometry = new THREE.IcosahedronGeometry(1.35, 3);
    const coreMaterial = new THREE.MeshStandardMaterial({
      color: 0x4263ff,
      wireframe: true,
      roughness: 0.1,
      metalness: 0.9,
      emissive: 0x203599,
      emissiveIntensity: 0.8,
    });
    const coreMesh = new THREE.Mesh(coreGeometry, coreMaterial);
    orbGroup.add(coreMesh);

    // 2. Inner Glowing Core
    const innerGeometry = new THREE.SphereGeometry(0.85, 32, 32);
    const innerMaterial = new THREE.MeshBasicMaterial({
      color: 0x20d9f2,
      wireframe: false,
      transparent: true,
      opacity: 0.45,
    });
    const innerMesh = new THREE.Mesh(innerGeometry, innerMaterial);
    orbGroup.add(innerMesh);

    // 3. Orbital Ring 1 (Electric Blue)
    const ring1Geometry = new THREE.TorusGeometry(1.85, 0.02, 16, 100);
    const ring1Material = new THREE.MeshBasicMaterial({
      color: 0x4263ff,
      transparent: true,
      opacity: 0.85,
    });
    const ring1 = new THREE.Mesh(ring1Geometry, ring1Material);
    ring1.rotation.x = Math.PI / 3;
    ring1.rotation.y = Math.PI / 6;
    orbGroup.add(ring1);

    // 4. Orbital Ring 2 (Violet Accent)
    const ring2Geometry = new THREE.TorusGeometry(2.1, 0.015, 16, 100);
    const ring2Material = new THREE.MeshBasicMaterial({
      color: 0x875bff,
      transparent: true,
      opacity: 0.7,
    });
    const ring2 = new THREE.Mesh(ring2Geometry, ring2Material);
    ring2.rotation.x = -Math.PI / 4;
    ring2.rotation.z = Math.PI / 4;
    orbGroup.add(ring2);

    // 5. Surrounding Particle Swarm
    const particleCount = 180;
    const particleGeometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    const blueColor = new THREE.Color(0x4263ff);
    const cyanColor = new THREE.Color(0x20d9f2);
    const violetColor = new THREE.Color(0x875bff);

    for (let i = 0; i < particleCount; i++) {
      const radius = 1.6 + Math.random() * 1.2;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      const colorChoice = Math.random();
      const chosenColor = colorChoice < 0.4 ? blueColor : colorChoice < 0.75 ? cyanColor : violetColor;
      colors[i * 3] = chosenColor.r;
      colors[i * 3 + 1] = chosenColor.g;
      colors[i * 3 + 2] = chosenColor.b;
    }

    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const particleMaterial = new THREE.PointsMaterial({
      size: 0.045,
      vertexColors: true,
      transparent: true,
      opacity: 0.8,
    });

    const particles = new THREE.Points(particleGeometry, particleMaterial);
    orbGroup.add(particles);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x20d9f2, 2.5, 50);
    pointLight.position.set(3, 3, 4);
    scene.add(pointLight);

    const violetLight = new THREE.PointLight(0x875bff, 2, 50);
    violetLight.position.set(-3, -2, 2);
    scene.add(violetLight);

    // Mouse interaction
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (event: MouseEvent) => {
      const rect = currentMount.getBoundingClientRect();
      const x = event.clientX - rect.left - rect.width / 2;
      const y = event.clientY - rect.top - rect.height / 2;
      targetX = (x / rect.width) * 0.8;
      targetY = (y / rect.height) * 0.8;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Animation loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (!prefersReducedMotion) {
        const elapsedTime = clock.getElapsedTime();

        // Smooth mouse lag follow
        mouseX += (targetX - mouseX) * 0.05;
        mouseY += (targetY - mouseY) * 0.05;

        orbGroup.rotation.y = elapsedTime * 0.35 + mouseX;
        orbGroup.rotation.x = Math.sin(elapsedTime * 0.2) * 0.15 + mouseY;

        ring1.rotation.z += 0.006;
        ring2.rotation.y -= 0.008;

        coreMesh.rotation.y -= 0.005;
        particles.rotation.y += 0.002;

        // Subtle breathing scale
        const scale = 1 + Math.sin(elapsedTime * 1.5) * 0.03;
        innerMesh.scale.set(scale, scale, scale);
      }

      renderer.render(scene, camera);
    };

    animate();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('mousemove', handleMouseMove);
      if (currentMount && renderer.domElement) {
        currentMount.removeChild(renderer.domElement);
      }
      renderer.dispose();
      coreGeometry.dispose();
      coreMaterial.dispose();
      innerGeometry.dispose();
      innerMaterial.dispose();
      ring1Geometry.dispose();
      ring1Material.dispose();
      ring2Geometry.dispose();
      ring2Material.dispose();
      particleGeometry.dispose();
      particleMaterial.dispose();
    };
  }, [size]);

  return (
    <div
      ref={mountRef}
      className={`relative flex items-center justify-center select-none ${className}`}
      style={{ width: size, height: size }}
    />
  );
};
