import pathlib

BASE = pathlib.Path('/Users/shswhuangyi/WorkBuddy/2026-07-13-13-45-31')
tpl = (BASE/'builder/template.html').read_text()
jszip = (BASE/'..').parent  # not used

jszip_path = pathlib.Path('/tmp/jszip.min.js')
gifenc_path = pathlib.Path('/tmp/gifenc.iife.js')

jszip = jszip_path.read_text()
gifenc = gifenc_path.read_text()

# 安全检查：内联库不能包含会截断 script 标签的字符串
for tag in ('</script',):
    if tag in jszip or tag in gifenc:
        raise SystemExit('库中包含危险字符串: '+tag)

out = tpl.replace('/*__JSZIP_LIB__*/', jszip).replace('/*__GIFENC_LIB__*/', gifenc)
dest = BASE/'dynamic_wallpaper_zip_generator.html'
dest.write_text(out)
print('written', dest, len(out), 'bytes')
print('jszip', len(jszip), 'gifenc', len(gifenc))
