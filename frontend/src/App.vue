<template>
  <main class="shell">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Vue + Django</p>
        <h1>项目工作台</h1>
        <p class="summary">
          后端已启用 simple-ui 管理后台和中文本地化，前端由 Vue 与 Vite 提供。
        </p>
      </div>
      <div class="actions" aria-label="服务入口">
        <a class="button primary" href="http://127.0.0.1:8000/admin/">管理后台</a>
        <a class="button secondary" href="http://127.0.0.1:8000/">Django 服务</a>
      </div>
    </section>

    <section class="status-grid" aria-label="项目状态">
      <article>
        <span>后端</span>
        <strong>Django 5.2</strong>
        <p>SQLite 已迁移，simple-ui 已加入应用配置。</p>
      </article>
      <article>
        <span>前端</span>
        <strong>Vue 3</strong>
        <p>Vite 项目已初始化并完成依赖安装。</p>
      </article>
      <article>
        <span>语言</span>
        <strong>中文</strong>
        <p>Django 语言为 zh-hans，时区为 Asia/Shanghai。</p>
      </article>
    </section>
  </main>
</template>
