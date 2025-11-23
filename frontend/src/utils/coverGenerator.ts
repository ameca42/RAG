export const generateCover = (title: string, topic: string, itemId: number, width: number, height: number): string => {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  if (!ctx) return '';

  // 1. 确定性随机配色 (根据 itemId)
  const seed = parseInt(String(itemId).slice(-1)) || 0;
  const gradients = [
      ['#FF9A9E', '#FECFEF'], ['#a18cd1', '#fbc2eb'], ['#84fab0', '#8fd3f4'],
      ['#fccb90', '#d57eeb'], ['#e0c3fc', '#8ec5fc'], ['#fa709a', '#fee140'],
      ['#4facfe', '#00f2fe'], ['#43e97b', '#38f9d7'], ['#30cfd0', '#330867'],
      ['#c471f5', '#fa71cd']
  ];
  const [color1, color2] = gradients[seed % gradients.length];

  // 2. 渐变背景
  const grd = ctx.createLinearGradient(0, 0, width, height);
  grd.addColorStop(0, color1);
  grd.addColorStop(1, color2);
  ctx.fillStyle = grd;
  ctx.fillRect(0, 0, width, height);

  // 3. 噪点纹理
  ctx.fillStyle = 'rgba(255,255,255,0.1)';
  for(let i=0; i<100; i++) {
      ctx.beginPath();
      ctx.arc(Math.random()*width, Math.random()*height, Math.random()*2, 0, Math.PI*2);
      ctx.fill();
  }

  // 4. 文字排版
  ctx.fillStyle = '#FFFFFF';
  ctx.shadowColor = 'rgba(0,0,0,0.1)';
  ctx.shadowBlur = 10;
  ctx.shadowOffsetY = 2;

  const fontSize = Math.floor(width / 9);
  ctx.font = `bold ${fontSize}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto`;
  ctx.textBaseline = 'middle';

  const words = title.split(' ');
  let line = '';
  let lines = [];
  const maxWidth = width - 60;

  for(let n = 0; n < words.length; n++) {
      const testLine = line + words[n] + ' ';
      const metrics = ctx.measureText(testLine);
      if (metrics.width > maxWidth && n > 0) {
          lines.push(line);
          line = words[n] + ' ';
      } else {
          line = testLine;
      }
  }
  lines.push(line);
  if (lines.length > 4) lines = lines.slice(0, 4);

  const lineHeight = fontSize * 1.3;
  const totalHeight = lines.length * lineHeight;
  const startY = (height - totalHeight) / 2;

  lines.forEach((l, i) => {
      ctx.fillText(l.trim(), 30, startY + (i * lineHeight));
  });

  // 5. 话题标签
  if (topic) {
      const tagText = `# ${topic}`;
      ctx.font = `bold ${Math.floor(width/20)}px sans-serif`;
      const tagWidth = ctx.measureText(tagText).width + 20;

      ctx.fillStyle = 'rgba(0,0,0,0.2)';
      // roundRect is not supported in all typescript defs yet, fallback or polyfill usually needed,
      // but standard browsers support it. Using rect for simplicity if strict type fails.
      if (ctx.roundRect) {
        ctx.beginPath();
        ctx.roundRect(30, startY - 40, tagWidth, 24, 12);
        ctx.fill();
      } else {
        ctx.fillRect(30, startY - 40, tagWidth, 24);
      }

      ctx.fillStyle = '#fff';
      ctx.fillText(tagText, 40, startY - 28);
  }

  // 6. 底部水印
  ctx.font = `${Math.floor(width/24)}px sans-serif`;
  ctx.fillStyle = 'rgba(255,255,255,0.8)';
  ctx.fillText('Hacker News', 30, height - 30);

  return canvas.toDataURL('image/jpeg', 0.8);
};

export const getRandomAspect = () => {
    const r = Math.random();
    if (r > 0.65) return { class: 'aspect-[3/4]', w: 600, h: 800 }; // 长图
    if (r > 0.35) return { class: 'aspect-square', w: 600, h: 600 }; // 方图
    return { class: 'aspect-[4/3]', w: 800, h: 600 }; // 短图
};