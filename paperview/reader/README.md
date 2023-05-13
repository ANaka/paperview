example url = `http://connect.biorxiv.org/biorxiv_xml.php?subject=neuroscience`

```bash
curl -X POST "http://127.0.0.1:8000/feeds/" -H  "accept: application/json" -H  "Content-Type: application/json" -d "{\"url\":\"http://connect.biorxiv.org/biorxiv_xml.php?subject=neuroscience\"}"
```