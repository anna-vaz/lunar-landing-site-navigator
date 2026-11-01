$ErrorActionPreference = "Stop"
$pp = New-Object -ComObject PowerPoint.Application
$deck = $pp.Presentations.Open("D:\Projects\nasa-space-apps-2026\pitch\Lunar_Landing_Site_Navigator.pptx", $true, $false, $false)
$out = "D:\Projects\nasa-space-apps-2026\pitch\render"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$i = 1
foreach ($s in $deck.Slides) { $s.Export("$out\slide$i.png", "PNG", 1600, 900); $i++ }
$deck.SaveAs("D:\Projects\nasa-space-apps-2026\pitch\Lunar_Landing_Site_Navigator.pdf", 32)
$deck.Close()
$pp.Quit()
"rendered $($i-1)"
