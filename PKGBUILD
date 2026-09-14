# Maintainer: iballz <balvinder0singh2000@gmail.com>
pkgname=hypr-tweaker-git
pkgver=1.0.0
pkgrel=1
pkgdesc="Modern Libadwaita / GTK4 visual configurator and live tweaker for Hyprland"
arch=('any')
url="https://github.com/iballz/hypr-tweaker"
license=('Apache-2.0')
depends=(
    'python'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'hyprland'
)
optdepends=(
    'polkit: for Intel Panel Self Refresh (PSR) toggling'
    'lua: for Caelestia modular dotfiles integration'
)
provides=('hypr-tweaker' 'caelestia-hypr-tweaker')
conflicts=('hypr-tweaker')
source=("git+https://github.com/iballz/hypr-tweaker.git")
md5sums=('SKIP')

pkgver() {
    cd "$srcdir/hypr-tweaker"
    git describe --long --tags --always 2>/dev/null | sed 's/^v//;s/\([^-]*-g\)/r\1/;s/-/./g' || echo "1.0.0"
}

package() {
    cd "$srcdir/hypr-tweaker"

    # Install launcher wrapper
    install -Dm755 bin/hypr-tweaker "$pkgdir/usr/bin/hypr-tweaker"
    ln -sf /usr/bin/hypr-tweaker "$pkgdir/usr/bin/caelestia-hypr-tweaker"

    # Install Python application files
    install -d "$pkgdir/usr/share/hypr-tweaker/src"
    install -Dm755 src/hypr_tweaker.py "$pkgdir/usr/share/hypr-tweaker/src/hypr_tweaker.py"
    install -Dm755 src/psr_helper.py "$pkgdir/usr/share/hypr-tweaker/src/psr_helper.py"
    install -Dm644 src/__init__.py "$pkgdir/usr/share/hypr-tweaker/src/__init__.py"

    # Install Desktop launcher
    install -Dm644 hypr-tweaker.desktop "$pkgdir/usr/share/applications/hypr-tweaker.desktop"

    # Install Icon
    install -Dm644 assets/hypr-tweaker.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/hypr-tweaker.svg"

    # Install License
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
