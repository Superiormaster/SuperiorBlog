
    const html = document.documentElement;
    const toggleBtn = document.getElementById('toggle-dark');

    // Apply system preference on first load if no user preference
    if (!localStorage.getItem('theme')) {
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            html.classList.add('dark');
        }
    } else {
        if (localStorage.getItem('theme') === 'dark') html.classList.add('dark');
        if (localStorage.getItem('theme') === 'light') html.classList.remove('dark');
    }

    // Toggle dark mode on button click
    toggleBtn.addEventListener('click', () => {
        html.classList.toggle('dark');
        if (html.classList.contains('dark')) {
            localStorage.setItem('theme', 'dark');
        } else {
            localStorage.setItem('theme', 'light');
        }
    });